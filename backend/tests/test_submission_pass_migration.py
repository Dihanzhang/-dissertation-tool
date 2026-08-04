from pathlib import Path


def test_payment_activation_function_is_not_executable_by_public_roles():
    migration = (Path(__file__).parents[1] / "migrations" / "001_submission_pass.sql").read_text()

    assert "revoke all on function public.fulfil_submission_pass" in migration
    assert "from public, anon, authenticated" in migration
    assert "grant execute on function public.fulfil_submission_pass" in migration
    assert "to service_role" in migration


def test_beta_redemption_migration_is_locked_to_service_role():
    migration = (Path(__file__).parents[1] / "migrations" / "002_beta_invites.sql").read_text()

    assert "create table public.beta_invites" in migration
    assert "alter table public.beta_invites enable row level security" in migration
    assert "create or replace function public.redeem_beta_invite" in migration
    assert "for update" in migration
    assert "revoke all on function public.redeem_beta_invite" in migration
    assert "from public, anon, authenticated" in migration
    assert "grant execute on function public.redeem_beta_invite" in migration
    assert "to service_role" in migration
