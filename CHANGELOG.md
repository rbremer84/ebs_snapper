# Changelog

## 0.8.0

- Add 'CostCenter' tag feature (#51)

## 0.7.4

- Fix issue with releasing on CircleCI, re-release 0.7.3 as 0.7.4

## 0.7.3

- Reduce I/O unit reservation for DynamoDB writes, clean up CFN paths (#47)

## 0.7.2

- Fix a permissions issue with invocation of Lambda functions via CloudWatch (#41)

## 0.7.1

- Use a replication alarm threshold more like the snapshot threshold, since it runs just as frequently (#40)
- Catch when too many snapshots are in progress and log it, vs. triggering a ticket (#40)
- Add CreateSnapshot permission explicitly to the role used by Lambda (#40)
- Adjust the CFN resources to be sure the trigger is setup correctly (#40)

## 0.7.0

- Support for cross-region snapshot replication (#38)
- Cleanup old versions of EBS Snapper functions during deployment (#37)
- Better error logging for bad configurations (#28)
- Centralize dummy AWS account number due to moto changes (#33)
- Better context objects and documentation (#35)

## 0.6.1

- Be sure we only touch retention when touching functions (#27)

## 0.6.0

- Ensure our log groups have default retention settings (#25)
- Documentation and metadata updates (#24)

## 0.5.0

- Add option to ignore retention settings, when necessary (#14)
- Test parse configs before saving (#18)
- Add support for ignoring certain volumes (#16)

## 0.4.2

- Freshen dependencies. No functional changes.

## 0.4.1

- Bump to release latest HEAD as 0.4.1, no changes from v0.4.0.

## 0.4.0

Much of this work is related to #5.

 - Switch to threading from multiprocess
 - Pre-create API data in bulk
 - Cut away the 'every DeleteOn tag' strategy
 - Randomize order of snapshot and cleanup
 - Make CLI perform full snapshot or cleanup
 - Log when a snapshot is completed, improve duration check
 - Reduce tag lookup calls, clean up, add more sleep

## 0.3.6

- Check for runtime length in more places (#9)
- Fix logging level issue (#8)

## 0.3.5

- Log when we go over the 4 minute timer for cleaning snapshots (#7)
- Don't error if snapshot missing (#7)

## 0.3.4

- Pass existing EC2 instance data to SNS instead of looking it up again (#6)
- Release as open source (issue numbers are reset to zero)

## 0.3.3

- Work to reduce alarms to more reasonable levels (#88)
- Clarify that no configs are created (#87)

## 0.3.2

- Be sure SNS methods take region arg (#86)
- Check for SNS message inputs (#84)

## 0.3.1

- Swallow errors on delete of a snapshot if the snapshot is in use by an AMI (#82)

## 0.3.0

- Add the ability to clean up snapshots iteratively (#79)
- Add timing measurements on cleanup (#66)
- Update docs to reflect not building it locally (#73)
- Don't copy `aws:` tags (#78)
- Bump to lambda-uploader's latest release (#53)
- Allow broader tags (#67)
- Add description to snapshots created (#74)
- Make deployments significantly faster for S3 (#71)
- Don't require lambda.json (#70)
- Don't error if invoked from console (#68)

## 0.2.0

- Introduce crontab syntax for backups (#62)
- Correct pylint testing to run correctly (#63)
- Add script to release/CD successful tagged builds to S3 (#50)
- Add flags to disable uploading, building, and stack updating to deploy command
- Add deploy command for deploying to new accounts (#58)
- Tweak thresholds for alerting (#57)

## 0.1.0

- Initial release. See [REQUIREMENTS.md](REQUIREMENTS.md) and [DESIGN.md](DESIGN.md) for initial design and requirements.
