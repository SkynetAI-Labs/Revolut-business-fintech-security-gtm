"""Additive database schema for transaction-monitoring alerts."""


def create_monitoring_tables(connection):
    """Create monitoring storage within the caller's transaction."""
    connection.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            rule_code TEXT NOT NULL CHECK (
                rule_code IN (
                    'LARGE_TRANSFER',
                    'HIGH_TRANSFER_FREQUENCY',
                    'HIGH_OUTGOING_VALUE',
                    'RAPID_REPEATED_TRANSFERS'
                )
            ),
            severity TEXT NOT NULL CHECK (severity IN ('medium', 'high')),
            evidence_json TEXT NOT NULL,
            transaction_at TEXT NOT NULL,
            detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'reviewed', 'dismissed')),
            reviewed_by INTEGER,
            reviewed_at TEXT,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (reviewed_by) REFERENCES users(id),
            UNIQUE (transaction_id, rule_code),
            CHECK (
                (status = 'open'
                 AND reviewed_by IS NULL AND reviewed_at IS NULL)
                OR
                (status IN ('reviewed', 'dismissed')
                 AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
            )
        )
    """)
    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_customer_status
        ON monitoring_alerts (customer_id, status, id)
    """)
