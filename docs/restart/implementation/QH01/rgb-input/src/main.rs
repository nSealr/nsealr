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

// Pillow11.1.0 Convert.c L24/rgb2l. Coefficients sum65536; for u8
// inputs the numerator is at most16744448, so u32 cannot overflow and
// the shifted result is0..255. Not the decimal299/587/114 rounding.
fn rgb_to_gray(r: u8, g: u8, b: u8) -> u8 {
    ((19595 * u32::from(r) + 38470 * u32::from(g) + 7471 * u32::from(b) + 32768) >> 16) as u8
}

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
    let mut image = rqrr::PreparedImage::prepare_from_greyscale(W, H, |x, y| {
        let at = (y * W + x) * 3;
        rgb_to_gray(rgb[at], rgb[at + 1], rgb[at + 2])
    });
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

#[cfg(test)]
mod tests {
    use super::rgb_to_gray;

    #[test]
    fn known_colors_and_rounding_discriminant() {
        for (r, g, b, expected) in [
            (0, 0, 0, 0),
            (255, 255, 255, 255),
            (255, 0, 0, 76),
            (0, 255, 0, 150),
            (0, 0, 255, 29),
            (0, 0, 250, 28),
            (0, 16, 0, 9),
            (240, 255, 255, 251),
        ] {
            assert_eq!(rgb_to_gray(r, g, b), expected);
        }
    }

    #[test]
    fn all_256_grays_are_preserved() {
        for gray in 0..=255 {
            assert_eq!(rgb_to_gray(gray, gray, gray), gray);
        }
    }

    #[test]
    fn arithmetic_range_bound() {
        let coefficients: u32 = 19595 + 38470 + 7471;
        assert_eq!(coefficients, 65536);
        let max_numerator: u32 = coefficients * 255 + 32768;
        assert_eq!(max_numerator, 16744448);
        assert!(max_numerator < u32::MAX);
        assert_eq!(32768_u32 >> 16, 0);
        assert_eq!(max_numerator >> 16, 255);
    }
}
