# Provider SARADC S3 fallibile: consegna pubblica

Fonte compilata `08d919c31cff329f14809cc8c3ed2f26cd8454c5`, dopo il merge
main `99332719` nello stesso worktree (`a5159582`). La precedente consegna OTG
`83331c5a` e il relativo packet restano immutati. Solo scalar3 pubblico;
nessuna identità reale, importazione, generazione, backup o recovery.

Il provider usa il percorso SDK SARADC con ownership RCC esclusiva, readback
espliciti, staging da 32 byte e risultato fallibile. Il core Rust e il clock
monotono in secondi restano invariati. L’adapter privato rifiuta errore o conteggi
diversi da 32, azzera il buffer posseduto e non fornisce fallback o firma.
Il helper SDK resta originale; l’adapter ripristina il gate APB posseduto dopo
enable, senza impulso di reset. Un refcount occupato resta intatto; corruzione
successiva del conteggio causa errore terminale, preservando il conteggio estraneo
e bilanciando i lock. Dopo disable i banchi DIG/data sono UNKNOWN perché gated.

Il packet esterno `s3-probe/artifacts/entropy-public` contiene 436 membri.
SHA256SUMS: `fa960732584895f48c6a11092753902d69f7d83b4ec5a569838de4aefc43e702`.
Closure: `2a0be16a7d442ff9cead668f119f077c1a8dac065308e4a417fd59375dc9cc09`.
L’app finale ha 448928 byte, SHA256
`0825678c8981aaabbf36be9377112905d8f2ea4cd6f06e010b6ef42045b9c969`.
Offset generati: boot 0x0, partition 0x8000, app 0x10000; DIO, 80m, 16MB,
nessun boot_app0. SDK 5.3 e099, TinyUSB 3.0.0 e toolchain restano quelli pinned.
Configurazione effettiva, macro, 94 input, 665 sorgenti compilati, libreria Rust,
ELF/map, licenze e attribuzioni sono legati nel packet. Audit finale 151 PASS.

I test mirati passano: 14 casi Rust e 1818 controlli del provider con ASan/UBSan.
Coprono errori, short/oversize, buffer/guard, sorgente grossolanamente bloccata,
readback, ownership/RCC, cleanup, cancellazione e tempi. Le ricevute 133/134
ripetono 128/129 e non aggiungono copertura. Il RED 135 era un errore di formato
nel nuovo C++ target, corretto senza cambiare SDK. Il build finale 139 passa in
4,08 s; 136 resta storico. Il disassemblato 146 stampava solo l’ultimo selector;
147 conserva separatamente tutti i corpi selezionati. Il packaging 149 cercava
un header nel path generico invece di platform_port: errore conservato, corretto
in 150 senza rebuild. Nessuna suite core/oracle/host immutata è stata ripetuta.
Le prove già valide 114 e 116/117 sono riusate; verificati integri tutti i 352
membri del vecchio packet. I gzip qui versionati ricostruiscono i byte originali.

Il vincolo ADC183 sul DIGADC2/doubleSAR in rev0.2 resta aperto per la produzione.
Quattro draw variati non qualificano entropia o salute analogica; i clock
configurati non sono frequenze fisiche calibrate. Le maschere WIFI/BT S3 sono
zero e non attestano RF spento. La scansione nominale e i riferimenti diretti
mostrano soltanto il consumer RNG del provider nell’app, senza competitori
ADC/I2S/temperatura/RF o writer persistenti nominali; non escludono tutta
l’attività indiretta, ROM o bootloader. I check da 50 ms sono fra chiamate,
non interrompono una chiamata SDK bloccata. Nessuna certificazione o nuova
campagna formale di min-entropia viene introdotta come requisito nascosto.

Il prossimo esperimento è finito e riservato a root dopo review distinta:
allo schermo locale, GPIO0 Skip oppure GPIO14 Run con gesto fresco; al massimo
quattro tentativi diagnostici da 32 byte, fermandosi al primo errore, poi nuova
conferma locale. Al massimo un nuovo draw ausiliario per il roundtrip scalar3,
con expectedPublicKey esplicita sul client e handle CDC mantenuto aperto.
I log compatti espongono bank/ref per i quattro snapshot, flag e riepilogo dei
registri abilitati; non ogni campo dei quattro snapshot conservati in RAM.
La consegna USB è distinta dall’accodamento. Un esito negativo va preservato,
senza ripetere finché verde. Dopo errore AUX occorre riavvio della CPU.

Stato provider: 242 byte INTERNAL, retention diagnostica: 2048 byte. Nessun
nuovo task/heap/DMA; main 98304 e USB 4096 byte INTERNAL. I frame selezionati
(464 byte massimo nuovo, collector 224) sono sostegno statico, non un limite
completo della catena ROM/indiretta. I minimi fisici main 4096 / USB 512 byte
liberi e la continuità LCD/pulsanti/CDC sono ancora da osservare su questo build.

L’amendment power ha review propria `5a9238d6` e binding `49d31b0f`, conservando
quelli storici. Il profilo S3 è USB-only, senza batteria/supercap/alimentazione
indipendente richiesta. La futura sessione reale termina alla perdita di power
e richiede reload locale; l’attuale fixture automatica non lo dimostra e non
prova erasure. E5 powered data-only unplug non applicabile. Pi/P4, stati,
criteri e dipendenze restano invariati; nessuna chiusura C01/H01 o readiness.

Nessun USB, flash, CI, push, merge o intervento eFuse dall’autore. La review
root di fonte/config/closure/packet e le evidenze fisiche restano distinte.
