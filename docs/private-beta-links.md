# Private beta links — how to run the beta

This replaces the old email sign-in beta. Testers no longer receive a magic-link
email, no longer create an account, and no longer pay. Each tester gets one
private web address that works on its own for 30 days.

Everything below is done by you. Testers only ever click their link.

---

## One-time setup: add the new table to Supabase

You only do this once.

1. Open [supabase.com](https://supabase.com) and sign in.
2. Open your project for the dissertation tool.
3. In the left sidebar, click **SQL Editor**.
4. Click **New query**.
5. Open the file `backend/migrations/003_beta_access_links.sql` in this repo,
   copy everything in it, and paste it into the query box.
6. Click **Run**.

You should see a success message. If it says something already exists, the
migration has already been applied and you can move on.

Nothing else in Supabase needs to change. Payments and paid passes are untouched.

---

## Create a link for one tester

Run this on your own computer, from the `backend` folder:

```
python -m app.tools.beta_links create --label tester-a
```

`--label` is just a short note so you can tell links apart later. Use something
like `tester-a`, `usc-1`, or `supervisor`. **Do not put an email address in the
label** — the command will refuse it.

The command prints the link **once**, like this:

```
Private beta link (shown once — copy it now, it is not recoverable):
  https://apa7.aithrival.com/beta/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

  link id:    3f7c... (use this to revoke)
  label:      tester-a
  expires at: 2026-09-04T...
```

Copy the link and the link id somewhere safe before closing the window. The link
itself cannot be shown again — only a scrambled version is stored — so if you
lose it, create a new one and revoke the old one.

If your `SITE_URL` is not set to the live site, add the address yourself:

```
python -m app.tools.beta_links create --label tester-a --site https://apa7.aithrival.com
```

---

## Send the link

Send it to the tester however you like — email, Teams, a message. Tell them:

> This link is personal, please don't forward or post it. Just open it and you
> can start reviewing straight away. No sign-in, no payment. It works for 30 days.

Because there is no email step, Outlook and USC mail scanners cannot break it.

---

## See which links exist

```
python -m app.tools.beta_links list
```

This shows each link's id, label, status, and expiry date. It never shows the
link itself.

---

## Revoke a link

If a link is shared around, or a tester finishes early:

```
python -m app.tools.beta_links revoke --id 3f7c...
```

Use the link id from `create` or `list`. It takes effect immediately — the next
time that person loads the page, they are locked out.

---

## What testers can and cannot do

They **can** run APA checks, upload documents, and download reviewed documents,
free, for 30 days.

They **cannot** reach the account page, buy anything, or affect any paying
customer. Their access expires on its own after 30 days with nothing to cancel.

---

## Things worth knowing

- A private link is a secret in a web address. Anyone who has the address has the
  access, so treat it like a password: send it directly, don't post it anywhere
  public, and revoke it if it spreads. Web addresses can also appear in server
  logs and browser history, which is why every link expires and can be revoked.
- Only a scrambled (hashed) version of each link is stored, so nobody — including
  anyone who could read the database — can recover a working link from Supabase.
- Testers are recorded by a random internal id, never by email address.
- The `/beta` address is not linked from the public site.
