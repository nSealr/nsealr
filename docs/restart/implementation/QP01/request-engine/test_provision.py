"""Producer refusal controls; real root-vendor builds are checked separately."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fixture_exchange', Path(__file__).with_name('exchange.py'))
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class ProducerControls(unittest.TestCase):
    def exercise(self, change, expected):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, manifest, artifact = root / 'main.rs', root / 'Cargo.toml', root / 'worker'
            source.write_text('frozen producer input')
            manifest.write_text('frozen manifest')
            artifact.write_bytes(b'\x7fELFpublic control only')
            artifact.chmod(0o755)
            row = {'reason': 'compiler-artifact', 'manifest_path': str(manifest),
                   'target': {'name': 'worker', 'kind': ['bin'], 'src_path': str(source)},
                   'filenames': [str(artifact)], 'executable': str(artifact)}
            def run(argv, **kwargs):
                self.assertEqual(kwargs['cwd'], root)
                rows = change(row, source, artifact)
                return subprocess.CompletedProcess(argv, 0, '\n'.join(json.dumps(x) for x in rows))
            with patch.object(producer, 'ROOT', root), patch.object(producer.subprocess, 'run', run):
                with self.assertRaisesRegex(RuntimeError, expected):
                    producer.build_artifact(['cargo', 'build', '--locked', '--offline'], source,
                                            manifest, 'worker', 'bin', ['main.rs', 'Cargo.toml'])

    def test_missing_or_ambiguous_artifact_refuses(self):
        for count in (0, 2):
            with self.subTest(count=count):
                self.exercise(lambda row, source, artifact: [row] * count, "missing/ambiguous artifact")

    def test_wrong_source_refuses(self):
        def change(row, source, artifact):
            row['target']['src_path'] = str(source.with_name('foreign.rs'))
            return [row]
        self.exercise(change, "wrong source or manifest")

    def test_wrong_manifest_refuses(self):
        def change(row, source, artifact):
            row['manifest_path'] = str(source.with_name('foreign.toml'))
            return [row]
        self.exercise(change, "wrong source or manifest")

    def test_changed_build_input_refuses(self):
        def change(row, source, artifact):
            source.write_text('changed during the build')
            return [row]
        self.exercise(change, "changed build input")

    def test_non_elf_refuses(self):
        def change(row, source, artifact):
            artifact.write_bytes(b'not an executable')
            return [row]
        self.exercise(change, "requires the actual ELF")


if __name__ == '__main__':
    unittest.main()
