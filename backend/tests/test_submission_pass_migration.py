from pathlib import Path


def test_payment_activation_function_is_not_executable_by_public_roles():
    migration = (Path(__file__).parents[1] / "migrations" / "001_submission_pass.sql").read_text()

    assert "revoke all on function public.fulfil_submission_pass" in migration
    assert "from public, anon, authenticated" in migration
    assert "grant execute on function public.fulfil_submission_pass" in migration
    assert "to service_role" in migration
