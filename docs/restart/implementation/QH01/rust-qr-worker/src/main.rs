//! Host-only, fixed public RGB experiment. No keys, QR argv or fixture output.
use std::io::{self, Read, Write};
use std::process::ExitCode;

extern "C" {
    fn setsid() -> i32;
}

const W: usize = 240;
const H: usize = 240;
const RAW: usize = W * H * 3;
const CAP: usize = 512;

struct Bounded {
    bytes: [u8; CAP],
    len: usize,
    overflow: bool,
    refused_chunk: usize,
}

impl Write for Bounded {
    fn write(&mut self, input: &[u8]) -> io::Result<usize> {
        // Check before every append, including a multi-byte upstream write.
        if input.len() > CAP - self.len {
            self.overflow = true;
            self.refused_chunk = input.len();
            return Err(io::ErrorKind::WriteZero.into());
        }
        self.bytes[self.len..self.len + input.len()].copy_from_slice(input);
        self.len += input.len();
        Ok(input.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

fn run() -> u8 {
    // Plain spawn's trusted bootstrap: parent independently queries kernel IDs.
    // SAFETY: setsid has no pointer argument; only this worker calls it.
    if unsafe { setsid() } < 0 {
        eprintln!(
            "status=session_error errno={:?}",
            io::Error::last_os_error().raw_os_error()
        );
        return 70;
    }
    let mut input = io::stdin().lock();
    let mut gate = [0_u8; 1];
    if input.read_exact(&mut gate).is_err() || gate != [b'G'] {
        return 71;
    }
    // Parent policy/readback precedes G. All image/decode work follows it.
    let mut rgb = vec![0_u8; RAW];
    if input.read_exact(&mut rgb).is_err() {
        eprintln!("status=short_input");
        return 72;
    }
    if rgb.chunks_exact(3).any(|c| c[0] != c[1] || c[1] != c[2]) {
        eprintln!("status=non_greyscale_fixture");
        return 73;
    }
    let mut image = rqrr::PreparedImage::prepare_from_greyscale(W, H, |x, y| rgb[(y * W + x) * 3]);
    let grids = image.detect_grids();
    if grids.is_empty() {
        eprintln!("status=no_qr grids=0");
        return 20;
    }
    if grids.len() != 1 {
        eprintln!("status=ambiguous grids={}", grids.len());
        return 21;
    }
    let mut staging = Bounded {
        bytes: [0; CAP],
        len: 0,
        overflow: false,
        refused_chunk: 0,
    };
    let decoded = grids[0].decode_to(&mut staging);
    if staging.overflow {
        eprintln!(
            "status=output_overflow retained={} limit={} refused_chunk={}",
            staging.len, CAP, staging.refused_chunk
        );
        return 42; // No staged partial bytes are sent to stdout.
    }
    if let Err(error) = decoded {
        eprintln!("status=decode_error error={error}");
        return 43;
    }
    // The Write warning about partial decode is handled by staging, not output.
    if io::stdout()
        .lock()
        .write_all(&staging.bytes[..staging.len])
        .is_err()
    {
        return 44;
    }
    eprintln!("status=decoded grids=1 bytes={}", staging.len);
    0
}

fn main() -> ExitCode {
    ExitCode::from(run())
}
