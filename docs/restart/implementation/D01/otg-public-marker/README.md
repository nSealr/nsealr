# S3 OTG CDC public marker delivery

Il firmware passa dal trasporto Serial/JTAG alla CDC OTG, mantenendo la richiesta
pubblica e il singolo motore Rust. Solo scalar3 noto; nessun endpoint di segreti,
entropy o recovery. Core, adapter Rust, clock in secondi, gesti della richiesta e
helper drain restano byte identici alla consegna a1e9052a. Host PR54 non toccato.

Fonte compilata: `1c5d5576b16f2c629d4a122cb6f361247ab2c498`.
Fonte del packet: `02fcd5313b96a917b520983bf509852dc53841f9`, solo README diverso.
Packet esterno nello stesso activeRoot: `s3-probe/artifacts/otg-public-marker`.
352 membri, SHA256SUMS `d171d652cea3b492c56eb92d8ca97a7d6ed2871eaa573701719767f9cfc9e89a`.
packet.json SHA `98b7ffc3753e9a9750ccae4b82dee03b94b7e4c72869ae9bf747a734c9f415d3`.

Build118 PASS4.08s; app439584byte, SHA
`be11531d68a180ed1ac6274967fe2ba8ea6794e0893471655714e210b5406541`.
Offset reali: boot0x0, partition0x8000, app0x10000; DIO/80m/16MB, niente boot_app0.
Stack main98304byte e USB4096byte INTERNAL richiesti; i minimi fisici devono ancora
essere misurati. Descrittori estratti dall ELF: due interfacce CDC class2/data10,
serial index0; niente JTAG, console o helper1200/DTR/ROM applicativi. Il mux resta
reversibile e i domini ROM/reset/debug non vengono disabilitati tramite eFuse.

Pin esp_tinyusb3.0.0 commit68bf7f, archiveaf8bc85b; SDK5.3 e099 invariato.
Preflight114 controlla tutti439membri. CMake verifica solo il manifesto; packet
lega archivio/CHECKSUMS/licenze,81 input app/core e664 sorgenti compilati.
Configurazione generata, macro effettive124, sezioni123 e simboli121/122 sono
incluse. Nessun writer nominale eseguibile trovato; non e una prova completa di
assenza di scritture indirette o attivita ROM. Il proxy UTMI Kconfig del componente
non attesta hardware S3: PM/wakeup spenti e FullSpeed effettivo.

Test116/117 PASS84 controlli ASan/UBSan: generazioni, vecchi callback durante
bus reset, due reset sovrapposti, saturazione sticky, marker corrotti, hold reset,
Both prioritario, fresh release e timer wrap. Nessuna campagna Rust/host ripetuta.
Ricevute112/113 iniziali e build115 precedente restano storiche, senza sostituire
il candidato finale. Il packet precedente289 membri e verificato integro; stessa
libreria Rust e input congelati, senza dedurre account pin dal solo replay90.

Revoca protetta da spinlock SAFE ISR/task, grant immutabile e nessun clear da
Enable. La barriera FIFO matching reset usa solo enqueue ISR nonblocking; se
persa, pending resta chiuso. Evento reset perso prima del hook rimane limite di
osservazione. Check dopo operazioni bloccanti/sign e prima/dopo accodamento TX.
RESULT QUEUED non attesta delivery; una revoca concorrente puo lasciare gia
accodato un prefisso o frame completo, e non lo richiama. Zero retry automatici.

I marker pubblici192byte sono in .noinit/.rtc_noinit/.dram0.bss NOBITS. Il report
previous/current ha ordine internal/RTC/BSS; invalido => sconosciuto, mai erasure.
Boot generation deriva da RTC valido o riparte1; non e nonce o prova affidabile
di continuita. La cattura inizia dopo startup SDK, non nella precedente finestra
ROM. Nuovo holdGPIO0 5s soloLocked permette isolare esp_restart; shortRotate e
BothLock restano distinti e richiedono gesto fresco.

L errore125 era del matcher di confezionamento: cercava il nome mangled in nm-C.
Originale e log conservati, matcher corretto in126 PASS senza cambiare firmware.
Integrita finale127 PASS:352membri,15ricevute legate, copie app/config/source/ELF.
Warning upstream di toolchain/CMake e manager volutamente disabilitato conservati.

Review distinta root e casi fisici OTG E0..E8 sono ancora da eseguire. Eventi non
comandabili o topologia non verificata sono NOT RUN/UNKNOWN. Le prove fisiche del
firmware Serial/JTAG rimangono storiche. Nessuna chiusura C01/H01, catalogo completo,
RAM erasure, custodia, entropy/recovery o readiness hardware e dichiarata.
