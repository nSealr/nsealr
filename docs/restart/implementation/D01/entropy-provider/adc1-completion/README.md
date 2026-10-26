# Osservatore di completamento ADC1: esperimento pubblico S3

Fonte compilata `e7f04215fc97808acdafdbf9420f6ef6d0102c5b`, base `f65e8aa9`.
La fonte precedente `08d919c3`, il packet e il singolo negativo fisico restano
immutati. Questa correzione riguarda soltanto provider, logica privata, test e
README dell’app. Core/Rust, ABI pubblica, protocollo, tempo, SDK, USB, host e piano
restano invariati; nessun passaggio implicito ad ADC1-only o RTC.

Due sequenze indipendenti clear → 0 osservato → nuovo 1 su ADC1_DONE_RAW bit31
precedono e seguono gli otto word RNG. L’adapter modifica soltanto il timer bit24
e il bit31 del registro WO/W1C; verifica il timer spento per clear e ripristinato
prima di ogni word, preservando gli altri campi. DONE iniziale 1 può essere
pulito normalmente; uno stale non pulibile o un evento mancante causa rifiuto.
Un unico budget monotono di 50 ms comprende claim, settle, entrambe le fasi e
cleanup, con 256 poll massimi per fase. Non interrompe una chiamata SDK bloccata.
Il completamento può appartenere a una conversione già in volo: non attesta che
sia iniziata soltanto dopo il trigger, che ADC2 funzioni o che il rumore basti.

DATA_STATUS resta diagnostico: `0x14000` contiene un risultato numerico a 12 bit
pari a zero, ma non è un codice di salute o freshness. La vecchia uguaglianza
non documentata è sostituita da un witness di completamento, conservando il
negativo di inattività quando il witness manca. Tutti gli schermi sui word
zero/FF/ripetuti/blocco duplicato rimangono. Il vecchio Health-6 fu un rifiuto
reale con 8 word campionati e 0 byte forniti, non una diagnosi RNG stuck; nessun
draw 1..4 fu osservato o passato. Receipt e raw originali sono in contract/.

Report privato sempre 384 byte: contatore <=8 e due byte fase occupano i quattro
byte del precedente contatore. Log bounded progress=pre/post in esadecimale:
bit0 lettura iniziale, bit1 iniziale 1, bit2 clear 0 osservato, bit3 nuovo 1.
Successo d/f per ciascuna fase; fase 0 non raggiunta. Stato 242 byte e retention
2048 byte INTERNAL, nessun task/heap/DMA nuovo. Stack main 98304 / USB 4096 byte
invariati; frame selezionati 464/240/48 byte, senza prova completa della catena
ROM/indiretta. I minimi fisici main 4096 / USB 512 byte liberi restano da misurare.

Host 152/153 PASS: 3485 controlli ASan/UBSan, incluso initial1 valido, raw stabile
con witness, stale/missing pre e post, timer restore, ownership, budget globale
cumulativo e claim, wipe/guard e tutti i negativi precedenti applicabili. Unico
build target 154 PASS in 4,08 s. Rust/core/USB e toolchain immutati sono riusati,
senza altro build Rust o campagna ripetuta. Questi test non qualificano hardware.

Packet esterno: `s3-probe/artifacts/entropy-adc1-completion`, 497 membri.
SHA256SUMS `28bf4e20449d02ab0241e7db7e9bb7cd9cba9753e33b7d7dd7d4d0d2136d5e56`.
Closure `ad3ff7d1ecab25d07ef4d5fc2cc355504a9ee889ed532f33f57ee4463d7dca3b`.
App 449600 byte SHA256
`7943dbcf4a1e389718b1959086487b6b13cdb50bb0f577ced9d4539c6d1fd7da`.
Flash args reali: boot 0x0, partition 0x8000, app 0x10000; DIO/80m/16MB,
nessun boot_app0. Config, 94 input, 665 sorgenti compilati, ELF/map/staticlib,
descrittori e riferimenti diretti legati nel packet; integrity164 PASS.
Macro145 riusata: sdkconfig.h e comandi provider/main identici; tutti i 665 comandi
uguali salvo il corretto PROJECT_VER 08d→e7 in esp_app_desc.

Errori di packaging preservati: 159 assumeva un alias preciso, ma il compilatore
ha unificato due lambda allo stesso indirizzo; 161 seleziona gruppi indirizzo e
size. 162 assumeva intero compile_commands identico; 163 accetta soltanto il delta
esatto PROJECT_VER previsto. Un errore di interpolazione del finalizer è stato
corretto prima del sigillo e la fonte fallita è conservata. Nessuno è un guasto
prodotto, né ha richiesto rebuild. I gzip ricostruiscono i byte originali.

Dopo review distinta root, una sola prova pubblica finita: un handle CDC aperto,
GPIO0 Skip o GPIO14 Run con gesto fresco; Run al massimo quattro diagnostici,
stop al primo errore, poi nuova conferma locale. Al massimo un nuovo ausiliario
scalar3 per boot CPU, con expectedPublicKey esplicita. Niente retry fino a verde.
Root osserva fasi, esito, display/pulsanti e watermark; segnali assenti UNKNOWN.
ADC183, qualificazione della sorgente e gate identità/reset/RAM/ROM restano aperti.
Profilo S3 USB-only invariato, nessuna batteria/supercap richiesta. Nessuna prova
di erasure, custodia o readiness. Nessun USB, flash, CI, push o merge dall’autore.
