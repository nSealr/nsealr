// Published NIP19/SeedQR fixtures only. Run against the pinned input commit.
use nsealr_core::{bip39::WordIndexes, nip19, session::{
    keyring::StatelessSessionKeyring, source_backup::session_source_backup_payload,
}};

fn main() {
    let secret = nip19::decode_nsec(
        "nsec1zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zyg3zygs4rm7hz"
    ).unwrap();
    let mut ring = StatelessSessionKeyring::new();
    ring.add_nsec("public fixture", &secret).unwrap();
    let source = ring.source_at(0).unwrap().clone();
    assert_eq!(source.nsec_secret_key, [0x11; 32]);
    let payload = session_source_backup_payload(&source).unwrap().clone();
    let indexes = WordIndexes::from_slice(&[115, 1325, 1154]).unwrap();
    let indexes_copy = indexes;
    println!("scalar={secret:?}\nsource={source:?}\nring={ring:?}");
    println!("indexes={indexes:?} copied={indexes_copy:?}\npayload={payload:?}");
    assert!(format!("{source:?}").contains("17, 17, 17"));
    assert!(format!("{payload:?}").contains("110, 115, 101, 99"));
    println!("UNSAFE BASELINE CONFIRMED: Debug reveals material; Clone, Copy, fields and direct backup work.");
}
