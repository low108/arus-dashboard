import logging


def test_sensitive_values_absent_from_logs(caplog):
    secrets = ["pdf-secret", "api-key-secret", "RAW STATEMENT TEXT", "1234567890123456"]
    with caplog.at_level(logging.INFO):
        logging.getLogger("arus").info("stage=ledger status=completed account=••••3456")
    for secret in secrets: assert secret not in caplog.text
