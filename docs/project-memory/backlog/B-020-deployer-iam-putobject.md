# B-020 — `static-site-deployer` IAM user cannot deploy (missing s3:PutObject)

**Type:** Bug
**Status:** Open
**Priority:** Medium
**Found:** S-2026-06-13-2215-l0-project-docs (2026-06-13)

## Summary

`make deploy` (→ `deploy.sh`) fails with `AccessDenied` for every upload when the
active AWS identity is `arn:aws:iam::635071011057:user/static-site-deployer`:

```
User: .../static-site-deployer is not authorized to perform: s3:PutObject
on resource "arn:aws:s3:::davidbmar-com/*" because no identity-based policy
allows the s3:PutObject action
```

The user can `s3:ListBucket` but not write. The L0 guinea-pig deploy only succeeded
by falling back to the admin profile: `AWS_PROFILE=bootstrap-admin make deploy`.

## Impact

Routine deploys require the **admin** account, violating least-privilege. Anyone
running `make deploy` without the admin profile gets a confusing half-failed sync
(the CloudFront invalidation never runs because `make` aborts).

## Fix

Attach an identity-based policy to `static-site-deployer` granting `s3:PutObject`,
`s3:DeleteObject` (deploy uses `aws s3 sync --delete`), and `s3:ListBucket` on
`arn:aws:s3:::davidbmar-com` and `arn:aws:s3:::davidbmar-com/*`, plus
`cloudfront:CreateInvalidation` on distribution `E3RCY6XA80ANRT`. Then deploys work
with the dedicated deployer and the admin account is no longer needed.

## Workaround (current)

`AWS_PROFILE=bootstrap-admin make deploy`
