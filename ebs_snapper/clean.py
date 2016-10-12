# -*- coding: utf-8 -*-
#
# Copyright 2016 Rackspace US, Inc.
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
"""Module for cleaning up snapshots."""

from __future__ import print_function
from time import sleep
import datetime
import json
import logging
import boto3
import dateutil
from ebs_snapper import utils, dynamo

LOG = logging.getLogger(__name__)


def perform_fanout_all_regions(context=None):
    """For every region, run the supplied function"""
    # get regions, regardless of instances
    sns_topic = utils.get_topic_arn('CleanSnapshotTopic')
    LOG.debug('perform_fanout_all_regions using SNS topic %s', sns_topic)

    regions = utils.get_regions(must_contain_instances=True)
    for region in regions:
        sleep(5) # API limit relief
        send_fanout_message(region=region, topic_arn=sns_topic)

    LOG.info('Function clean_perform_fanout_all_regions completed')


def send_fanout_message(region, topic_arn, context=None):
    """Publish an SNS message to topic_arn that specifies a region to review snapshots on"""
    message = json.dumps({'region': region})
    LOG.debug('send_fanout_message: %s', message)

    utils.sns_publish(TopicArn=topic_arn, Message=message)
    LOG.info('Function clean_send_fanout_message completed')


def clean_snapshot(region,
                   installed_region='us-east-1',
                   started_run=datetime.datetime.now(dateutil.tz.tzutc()),
                   context=None):
    """Check the region see if we should clean up any snapshots"""
    LOG.info('clean_snapshot in region %s', region)

    owner_ids = utils.get_owner_id(region, context=context)
    LOG.info('Filtering snapshots to clean by owner id %s', owner_ids)

    configurations = dynamo.list_configurations(installed_region)
    LOG.info('Fetched all possible configuration rules from DynamoDB')

    # go clean up 5 tags at a time, until they are all gone, and time it!
    tags_seen = []
    deleted_count = 0
    batch_size = 5

    delete_on_date = datetime.date.today()
    # go get initial batch, as long as there are tags and we still have time
    tags_to_cleanup = utils.find_deleteon_tags(region, delete_on_date, max_tags=batch_size)
    while len(tags_to_cleanup) > 0 and not timeout_check(started_run, 'clean_snapshot'):
        LOG.info('Pulling %s (batch size) tags to clean up, found: %s',
                 batch_size,
                 str(tags_to_cleanup))

        for target_tag in tags_to_cleanup:
            LOG.info('Loop in clean_snapshot, looking at tag %s', target_tag)
            tags_seen.append(target_tag)

            # always sleep for 5 seconds before we clean up another chunk of snapshots
            sleep(5)  # help with API limit

            if timeout_check(started_run, 'clean_snapshot'):
                LOG.warn('clean_snapshot timed out')
                break

            # now go get 'em!
            deleted_count += clean_snapshots_tagged(
                started_run,
                target_tag,
                owner_ids,
                region,
                configurations)

        # check before we look for newer tags to cleanup, that we're good to run
        if timeout_check(started_run, 'Timed out while cleaning snapshots'):
            LOG.warn('clean_snapshot timed out')
            break

        # another batch, more tags after the first batch_size
        tags_to_cleanup = utils.find_deleteon_tags(region, delete_on_date, max_tags=batch_size)
        # but don't try to do a tag if we already tried.
        tags_to_cleanup = [x for x in tags_to_cleanup if x not in tags_seen]

    if deleted_count <= 0:
        LOG.warn('No snapshots were cleaned up for the entire region %s', region)

    LOG.info('Function clean_snapshot completed')


def clean_snapshots_tagged(start_time, delete_on,
                           owner_ids, region, configurations, default_min_snaps=5):
    """Remove snapshots where DeleteOn tag is delete_on string"""
    ec2 = boto3.client('ec2', region_name=region)

    # pull down snapshots we want to axe
    filters = [
        {'Name': 'tag-key', 'Values': ['DeleteOn']},
        {'Name': 'tag-value', 'Values': [delete_on]},
    ]
    LOG.debug("ec2.describe_snapshots with filters %s", filters)
    sleep(1)  # help with API limit
    snapshot_response = ec2.describe_snapshots(OwnerIds=owner_ids, Filters=filters)
    LOG.debug("ec2.describe_snapshots fin")

    deleted_count = 0
    if 'Snapshots' not in snapshot_response or len(snapshot_response['Snapshots']) <= 0:
        LOG.debug('No snapshots were found using owners=%s, filters=%s',
                  owner_ids,
                  filters)
        return deleted_count
    else:
        LOG.info('Examining %s snapshots to clean delete_on=%s, region=%s',
                 str(len(snapshot_response['Snapshots'])),
                 delete_on,
                 region)

    for snap in snapshot_response['Snapshots']:
        # be sure we haven't overrun the time to run
        if timeout_check(start_time, 'clean_snapshots_tagged snap loop'):
            return deleted_count

        sleep(1)  # help with API limit

        # attempt to identify the instance this applies to, so we can check minimums
        try:
            snapshot_volume = snap['VolumeId']
            volume_instance = utils.get_instance_by_volume(snapshot_volume, region)

            # minimum required
            if volume_instance is None:
                minimum_snaps = default_min_snaps
            else:
                snapshot_settings = utils.get_snapshot_settings_by_instance(
                    volume_instance, configurations, region)
                minimum_snaps = snapshot_settings['snapshot']['minimum']

            # current number of snapshots
            no_snaps = utils.count_snapshots(snapshot_volume, region)

            # if we have less than the minimum, don't delete this one
            if no_snaps < minimum_snaps:
                LOG.warn('Not deleting snapshot %s from %s', snap['SnapshotId'], region)
                LOG.warn('Only %s snapshots exist, below minimum of %s', no_snaps, minimum_snaps)
                continue

        except:
            # if we couldn't figure out a minimum of snapshots,
            # don't clean this up -- these could be orphaned snapshots
            LOG.warn('Not deleting snapshot %s from %s, not enough snapshots remain',
                     snap['SnapshotId'], region)
            continue

        LOG.warn('Deleting snapshot %s from %s', snap['SnapshotId'], region)
        deleted_count += utils.delete_snapshot(snap['SnapshotId'], region)

    LOG.info('Function clean_snapshots_tagged completed, deleted count: %s', str(deleted_count))
    return deleted_count


def timeout_check(start_time, place):
    """Return True if start_time was more than 4 minutes ago"""
    elapsed_time = datetime.datetime.now(dateutil.tz.tzutc()) - start_time
    if elapsed_time >= datetime.timedelta(minutes=4):
        LOG.warn('%s timed out', place)
        return True

    return False
