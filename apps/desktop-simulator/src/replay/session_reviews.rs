//! `session-import-reviews` / `session-source-backups` replay: rebuild the
//! RAM-only session source from the referenced `source_vector`, then assert the
//! secret-hiding import/backup review (review_id, approval_digest, pages,
//! fingerprint) — and, for backups, the revealed payload — match the vector
//! exactly.

use super::{assert_review_pages, build_session_key_source, str_field, ReplayResult};
use nsealr_core::session::import_review::{
    build_session_import_review, session_key_source_fingerprint,
};
use nsealr_core::session::source_backup::{
    build_session_source_backup_review, run_session_source_backup_flow,
};
use serde_json::Value;

fn source_of(value: &Value) -> Result<nsealr_core::session::keyring::SessionKeySource, String> {
    build_session_key_source(
        str_field(value, "source_type")?,
        str_field(value, "source_vector")?,
        str_field(value, "label")?,
    )
}

pub(super) fn replay_import(value: &Value) -> ReplayResult {
    let source = source_of(value)?;
    let fingerprint = session_key_source_fingerprint(&source);
    if fingerprint.as_str() != str_field(value, "fingerprint")? {
        return Err(format!(
            "fingerprint {} != vector.fingerprint {}",
            fingerprint.as_str(),
            str_field(value, "fingerprint")?
        ));
    }
    let review = build_session_import_review(&source);
    if review.review_id.as_str() != str_field(value, "review_id")? {
        return Err("review_id != vector.review_id".into());
    }
    if review.approval_digest.as_str() != str_field(value, "approval_digest")? {
        return Err("approval_digest != vector.approval_digest".into());
    }
    let pages = value
        .get("pages")
        .and_then(Value::as_array)
        .ok_or("missing 'pages'")?;
    assert_review_pages("session-import-review", &review.pages, pages)
}

pub(super) fn replay_backup(value: &Value) -> ReplayResult {
    let source = source_of(value)?;
    let fingerprint = session_key_source_fingerprint(&source);
    if fingerprint.as_str() != str_field(value, "fingerprint")? {
        return Err("fingerprint != vector.fingerprint".into());
    }
    let review = build_session_source_backup_review(&source);
    if review.review_id.as_str() != str_field(value, "review_id")? {
        return Err("review_id != vector.review_id".into());
    }
    if review.approval_digest.as_str() != str_field(value, "approval_digest")? {
        return Err("approval_digest != vector.approval_digest".into());
    }
    let pages = value
        .get("pages")
        .and_then(Value::as_array)
        .ok_or("missing 'pages'")?;
    assert_review_pages("session-source-backup-review", &review.pages, pages)?;

    // The revealed backup payload matches the vector's declared secret material.
    let result = run_session_source_backup_flow(
        &source,
        &[
            nsealr_core::review::controls::ReviewButton::Next,
            nsealr_core::review::controls::ReviewButton::Approve,
        ],
        2,
    )
    .map_err(|e| format!("backup fixture flow: {e:?}"))?;
    let payload = result
        .backup_payload
        .ok_or("approved fixture backup missing")?;
    if payload.backup_format != str_field(value, "backup_format")? {
        return Err(format!(
            "backup_format '{}' != vector '{}'",
            payload.backup_format,
            str_field(value, "backup_format")?
        ));
    }
    let want = value
        .get("backup_payload")
        .ok_or("missing 'backup_payload'")?;
    match payload.backup_format {
        "nip19_nsec" => check(want, "nsec", payload.reveal_nsec()),
        "bip39_words_seedqr" => {
            check(want, "mnemonic", payload.reveal_mnemonic())?;
            check(
                want,
                "standard_seedqr_digits",
                payload.reveal_standard_seedqr_digits(),
            )?;
            check(
                want,
                "compact_seedqr_hex",
                payload.reveal_compact_seedqr_hex(),
            )
        }
        other => Err(format!("unexpected backup_format '{other}'")),
    }
}

fn check(want: &Value, key: &str, got: &str) -> ReplayResult {
    let expected = str_field(want, key)?;
    if got == expected {
        Ok(())
    } else {
        Err(format!("backup_payload.{key} differs from fixture"))
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn backup_mismatch_does_not_echo_secret_output() {
        let fixture = serde_json::json!({"nsec": "public fixture expected"});
        let error = super::check(&fixture, "nsec", "public fixture actual").unwrap_err();
        assert_eq!(error, "backup_payload.nsec differs from fixture");
    }
}
