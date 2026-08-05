# Beta links — how to give a tester free access

A beta link is one web address that lets one person use the review tool free for
30 days. No sign-in, no payment, no account.

You do everything from the Supabase website. You never need to open a terminal.

---

## Step 1 — Set this up (once only)

1. Go to **supabase.com** and sign in.
2. Click your dissertation tool project.
3. In the menu on the left, click **SQL Editor**.
4. Click **New query**.
5. Open the file `backend/migrations/003_beta_access_links.sql` from this
   project, select all of it, copy it, and paste it into the big empty box.
6. Click **Run**.

You should see "Success". You never have to do this step again.

---

## Step 2 — Make a link for a tester

1. In Supabase, click **SQL Editor**, then **New query**.
2. Paste this in, changing `tester-a` to a short nickname for that person:

```sql
select 'https://apa7.aithrival.com/beta/' || create_beta_access_link('tester-a') as link;
```

3. Click **Run**.

A result appears with one box containing the full web address. **Copy it now and
save it somewhere.** You cannot look it up again later — the system deliberately
does not keep a copy. If you lose it, just make a new one.

Use a nickname you'll recognise, like `tester-a`, `jane-supervisor`, or
`usc-group-1`. **Do not use an email address** — it will refuse.

---

## Step 3 — Send it

Send the address to your tester by email or message, with something like:

> Here's your personal link to the tool. Please don't forward it to anyone else.
> Just click it and you can start straight away — nothing to sign up for and
> nothing to pay. It works for 30 days.

That's it. When they click it, the tool opens and they can use it.

---

## To see who has a link

**SQL Editor** → **New query** → paste → **Run**:

```sql
select label, status, expires_at from beta_access_links order by created_at desc;
```

This shows the nicknames, whether each link still works, and when it stops
working. It does not show the links themselves.

---

## To switch a link off

If a link gets shared around, or someone finishes early. Change `tester-a` to
that person's nickname:

```sql
update beta_access_links set status = 'revoked', revoked_at = now()
where label = 'tester-a';
```

Click **Run**. It stops working immediately.

---

## Good to know

- **Links expire on their own after 30 days.** There is nothing to cancel and
  nobody gets charged, ever.
- **Treat a link like a password.** Anyone holding the address can use the tool.
  Send it directly to one person, don't post it publicly, and switch it off if it
  spreads.
- **Testers can't reach anything to do with money.** They cannot see the account
  page, cannot buy anything, and cannot affect paying customers.
- **You are not storing anyone's email.** Each link is recorded under the
  nickname you chose and a random internal number.
- **Nobody can recover a link from the database**, including you. Only a
  scrambled version is kept, which is what makes it safe to store.

---

## For developers

There is also a command-line equivalent, if the Supabase service-role key is
present in `backend/.env`:

```
python -m app.tools.beta_links create --label tester-a --site https://apa7.aithrival.com
python -m app.tools.beta_links list
python -m app.tools.beta_links revoke --id <link id>
```

It does the same thing as the SQL above: generates 32 random bytes, stores only
the SHA-256 hash, and prints the raw link once.
