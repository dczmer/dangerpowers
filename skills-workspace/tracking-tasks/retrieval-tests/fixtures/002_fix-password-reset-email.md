---
title: "fix: password reset email intermittently never sent"
type: bug
state: open
author: "sam"
created: 2026-10-02
updated: 2026-10-05
tags: [auth, email]
---

# fix: password reset email intermittently never sent

## Why
Roughly one in five password reset requests on staging never produce an
email, and support has no way to tell which users are affected.

## Reproduction
1. From the staging login page, click "Forgot password" for a known test
   account.
2. Submit the reset form and watch the mail spool.

## Expected
A reset email arrives within a minute.

## Actual
No email arrives for some accounts; `mailer.log` shows the send call is
never made for those requests.

## Environment
Staging, reproducible since 2026-09-28.
