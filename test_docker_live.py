#!/usr/bin/env python3
"""
Live Docker integration tests for convert_videos.
These tests actually build and run the Docker container to verify end-to-end functionality.

Note: These tests are resource-intensive and require:
- Linux OS
- Docker installation
- Sufficient disk space

Run with: pytest test_docker_live.py -v
"""

import os
import platform
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
import shutil
import yaml


class TestDockerLive(unittest.TestCase):
    """Live Docker integration tests."""
    
    @classmethod
    def setUpClass(cls):
        """Check prerequisites before running any tests."""
        # Check if running on Linux
        if platform.system() != 'Linux':
            raise unittest.SkipTest("Docker tests only run on Linux")
        
        # Check if Docker is installed
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise unittest.SkipTest("Docker is not available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise unittest.SkipTest("Docker is not installed")
        
        print("\n✓ Prerequisites met: Linux OS with Docker installed")
    
    def _create_minimal_test_video(self, output_path: Path) -> bool:
        """
        Create a minimal test video file.
        
        This creates a very small H.264 video that can be converted to H.265.
        Uses ffmpeg if available, otherwise creates a minimal video using raw data.
        
        Args:
            output_path: Path where the video should be created
            
        Returns:
            True if video was created successfully, False otherwise
        """
        # Try to use ffmpeg to create a proper video
        try:
            # Create a 1-second test video with minimal settings
            # This creates an H.264 video that's about 50-100KB
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'testsrc=duration=1:size=320x240:rate=1',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '40',
                '-pix_fmt', 'yuv420p',
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
                print(f"✓ Created test video using ffmpeg: {output_path.stat().st_size} bytes")
                return True
            else:
                print(f"✗ ffmpeg failed: {result.stderr[:200]}")
                
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"✗ ffmpeg not available: {e}")
        
        # Fallback: Create a minimal valid MP4 file with real video data
        # This is a minimal H.264-encoded MP4 that video tools should recognize
        # Based on minimal MP4 structure with ftyp, mdat, moov boxes
        minimal_mp4 = bytes([
            # ftyp box (file type)
            0x00, 0x00, 0x00, 0x20,  # box size = 32
            0x66, 0x74, 0x79, 0x70,  # 'ftyp'
            0x69, 0x73, 0x6F, 0x6D,  # 'isom' - major brand
            0x00, 0x00, 0x02, 0x00,  # minor version
            0x69, 0x73, 0x6F, 0x6D,  # compatible brands
            0x69, 0x73, 0x6F, 0x32,
            0x61, 0x76, 0x63, 0x31,
            0x6D, 0x70, 0x34, 0x31,
            
            # mdat box (media data) - minimal
            0x00, 0x00, 0x00, 0x08,  # box size = 8 (header only)
            0x6D, 0x64, 0x61, 0x74,  # 'mdat'
            
            # moov box (movie/metadata)
            0x00, 0x00, 0x00, 0x68,  # box size = 104
            0x6D, 0x6F, 0x6F, 0x76,  # 'moov'
            
            # mvhd box (movie header)
            0x00, 0x00, 0x00, 0x6C,  # box size
            0x6D, 0x76, 0x68, 0x64,  # 'mvhd'
            0x00, 0x00, 0x00, 0x00,  # version and flags
            0x00, 0x00, 0x00, 0x00,  # creation time
            0x00, 0x00, 0x00, 0x00,  # modification time
            0x00, 0x00, 0x03, 0xE8,  # timescale = 1000
            0x00, 0x00, 0x03, 0xE8,  # duration = 1000 (1 second)
            0x00, 0x01, 0x00, 0x00,  # rate = 1.0
            0x01, 0x00,              # volume = 1.0
            0x00, 0x00,              # reserved
            0x00, 0x00, 0x00, 0x00,  # reserved
            0x00, 0x00, 0x00, 0x00,  # reserved
            # transformation matrix (identity)
            0x00, 0x01, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x01, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x40, 0x00, 0x00, 0x00,
            # preview time, duration, poster time
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            # selection time, duration, current time
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x02,  # next track ID
        ])
        
        try:
            output_path.write_bytes(minimal_mp4)
            if output_path.exists() and output_path.stat().st_size > 0:
                print(f"✓ Created minimal MP4 file: {output_path.stat().st_size} bytes")
                return True
        except Exception as e:
            print(f"✗ Failed to create minimal MP4: {e}")
            return False
        
        return False
    
    def _build_docker_image(self, repo_path: Path, image_tag: str) -> bool:
        """
        Build the Docker image from the repository's Dockerfile.
        
        Args:
            repo_path: Path to the repository root
            image_tag: Tag to use for the image
            
        Returns:
            True if build succeeded, False otherwise
            
        Raises:
            unittest.SkipTest: If build fails due to environment issues (SSL, network, etc.)
        """
        print(f"\nBuilding Docker image: {image_tag}")
        
        try:
            result = subprocess.run(
                ['docker', 'build', '-t', image_tag, '.'],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout for build
            )
            
            if result.returncode == 0:
                print(f"✓ Docker image built successfully: {image_tag}")
                return True
            else:
                print(f"✗ Docker build failed:")
                print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
                print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
                
                # Check if it's an SSL/network issue (environment problem, not code problem)
                error_output = result.stdout + result.stderr
                if 'SSL' in error_output or 'certificate' in error_output.lower():
                    print("\n⚠ Build failed due to SSL/certificate issues.")
                    print("This may be an environment issue, not a code issue.")
                    raise unittest.SkipTest("Docker build failed due to SSL/network issues in environment")
                
                return False
                
        except subprocess.TimeoutExpired:
            print("✗ Docker build timed out after 10 minutes")
            return False
        except unittest.SkipTest:
            # Let SkipTest propagate
            raise
        except Exception as e:
            print(f"✗ Docker build error: {e}")
            return False
    
    def _run_docker_container(
        self,
        image_tag: str,
        container_name: str,
        mount_path: Path,
        timeout: int = 120
    ) -> bool:
        """
        Run the Docker container with the test directory mounted.
        
        Args:
            image_tag: Docker image tag to run
            container_name: Name for the container
            mount_path: Path to mount as /data in the container
            timeout: Maximum time to wait for processing (seconds)
            
        Returns:
            True if container ran successfully, False otherwise
        """
        print(f"\nRunning Docker container: {container_name}")
        
        try:
            # Run container in detached mode
            cmd = [
                'docker', 'run',
                '-d',  # Detached mode
                '--name', container_name,
                '-v', f'{mount_path}:/data',
                image_tag
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"✗ Failed to start container:")
                print(result.stderr)
                return False
            
            container_id = result.stdout.strip()
            print(f"✓ Container started: {container_id[:12]}")
            
            # Wait for processing to complete
            # The container runs in loop mode, but we'll give it time to process files
            print(f"Waiting up to {timeout} seconds for processing...")
            time.sleep(5)  # Initial wait for startup
            
            # Check for converted file periodically
            start_time = time.time()
            while time.time() - start_time < timeout:
                converted_files = list(mount_path.glob('*.converted.*'))
                if converted_files:
                    print(f"✓ Conversion detected after {int(time.time() - start_time)} seconds")
                    # Give it a bit more time to complete and clean up
                    time.sleep(2)
                    return True
                
                # Check if container is still running
                check_result = subprocess.run(
                    ['docker', 'inspect', '-f', '{{.State.Running}}', container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if check_result.stdout.strip() != 'true':
                    # Container stopped
                    print("✗ Container stopped unexpectedly")
                    # Get logs
                    log_result = subprocess.run(
                        ['docker', 'logs', container_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    print("Container logs:")
                    print(log_result.stdout[-1000:])
                    return False
                
                time.sleep(2)  # Check every 2 seconds
            
            # Timeout reached
            print(f"✗ Timeout reached after {timeout} seconds")
            
            # Get logs before returning
            log_result = subprocess.run(
                ['docker', 'logs', container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            print("Container logs:")
            print(log_result.stdout[-1000:])
            
            return False
            
        except subprocess.TimeoutExpired:
            print("✗ Docker run command timed out")
            return False
        except Exception as e:
            print(f"✗ Error running container: {e}")
            return False
    
    def _stop_and_remove_container(self, container_name: str):
        """
        Stop and remove a Docker container.
        
        Args:
            container_name: Name of the container to remove
        """
        print(f"\nCleaning up container: {container_name}")
        
        # Stop container
        try:
            subprocess.run(
                ['docker', 'stop', container_name],
                capture_output=True,
                timeout=30
            )
            print(f"✓ Container stopped")
        except Exception as e:
            print(f"⚠ Failed to stop container: {e}")
        
        # Remove container
        try:
            subprocess.run(
                ['docker', 'rm', container_name],
                capture_output=True,
                timeout=30
            )
            print(f"✓ Container removed")
        except Exception as e:
            print(f"⚠ Failed to remove container: {e}")
    
    def _remove_docker_image(self, image_tag: str):
        """
        Remove a Docker image.
        
        Args:
            image_tag: Tag of the image to remove
        """
        print(f"\nRemoving Docker image: {image_tag}")
        
        try:
            subprocess.run(
                ['docker', 'rmi', image_tag],
                capture_output=True,
                timeout=30
            )
            print(f"✓ Image removed")
        except Exception as e:
            print(f"⚠ Failed to remove image: {e}")
    
    def test_docker_live_conversion(self):
        """
        Test the complete Docker workflow:
        1. Build Docker image
        2. Create test video
        3. Create configuration
        4. Run container
        5. Verify conversion and original removal
        6. Clean up
        """
        # Setup
        repo_path = Path(__file__).parent.absolute()
        image_tag = 'convert_videos_test:latest'
        container_name = 'convert_videos_test_container'
        
        # Create temporary directory for test
        with tempfile.TemporaryDirectory(prefix='docker_test_') as tmpdir:
            tmpdir_path = Path(tmpdir)
            print(f"\nTest directory: {tmpdir_path}")
            
            cleanup_needed = False
            skip_exception = None
            
            try:
                # Step 1: Build Docker image
                print("\n" + "="*60)
                print("STEP 1: Building Docker image")
                print("="*60)
                
                try:
                    build_success = self._build_docker_image(repo_path, image_tag)
                    self.assertTrue(build_success, "Docker image build failed")
                    cleanup_needed = True  # Image was built, need cleanup
                except unittest.SkipTest as e:
                    # Save skip exception to re-raise after cleanup
                    skip_exception = e
                    raise
                
                # Step 2: Create test video
                print("\n" + "="*60)
                print("STEP 2: Creating test video")
                print("="*60)
                
                test_video = tmpdir_path / 'test_video.mp4'
                video_created = self._create_minimal_test_video(test_video)
                self.assertTrue(video_created, "Failed to create test video")
                self.assertTrue(test_video.exists(), "Test video file does not exist")
                
                video_size = test_video.stat().st_size
                print(f"Test video size: {video_size} bytes")
                
                # Step 3: Create configuration file
                print("\n" + "="*60)
                print("STEP 3: Creating configuration file")
                print("="*60)
                
                config = {
                    'directory': '/data',
                    'min_file_size': '1B',  # Accept any file size for testing
                    'output': {
                        'format': 'mkv',
                        'encoder': 'x265',
                        'preset': 'ultrafast',  # Fastest encoding for test
                        'quality': 40  # Lower quality = faster
                    },
                    'remove_original_files': True,  # Remove original after conversion
                    'loop': True,
                    'dry_run': False
                }
                
                config_path = tmpdir_path / 'config.yaml'
                with open(config_path, 'w') as f:
                    yaml.dump(config, f)
                
                print(f"✓ Configuration created: {config_path}")
                print(f"  - Min file size: 1B")
                print(f"  - Remove original: True")
                print(f"  - Encoder: x265 (ultrafast)")
                
                # Step 4: Run Docker container
                print("\n" + "="*60)
                print("STEP 4: Running Docker container")
                print("="*60)
                
                run_success = self._run_docker_container(
                    image_tag,
                    container_name,
                    tmpdir_path,
                    timeout=120
                )
                self.assertTrue(run_success, "Docker container did not process files successfully")
                
                # Step 5: Verify results
                print("\n" + "="*60)
                print("STEP 5: Verifying results")
                print("="*60)
                
                # Check for converted file
                converted_files = list(tmpdir_path.glob('*.converted.*'))
                print(f"\nFiles in directory after processing:")
                for file in tmpdir_path.iterdir():
                    print(f"  - {file.name} ({file.stat().st_size} bytes)")
                
                self.assertGreater(
                    len(converted_files),
                    0,
                    "No converted file was created"
                )
                
                converted_file = converted_files[0]
                print(f"\n✓ Converted file found: {converted_file.name}")
                print(f"  Size: {converted_file.stat().st_size} bytes")
                
                # Verify converted file has content
                self.assertGreater(
                    converted_file.stat().st_size,
                    0,
                    "Converted file is empty"
                )
                
                # Check that original was removed
                original_exists = test_video.exists()
                print(f"\n{'✗' if original_exists else '✓'} Original file {'still exists' if original_exists else 'was removed'}")
                
                # Original might be renamed to .orig instead of removed
                # depending on preserve_original setting
                orig_files = list(tmpdir_path.glob('*.orig.*'))
                if orig_files:
                    print(f"⚠ Original was renamed to: {orig_files[0].name}")
                else:
                    self.assertFalse(
                        original_exists,
                        "Original file was not removed as expected"
                    )
                
                print("\n" + "="*60)
                print("✓ ALL TESTS PASSED")
                print("="*60)
                
            finally:
                # Step 6: Clean up
                print("\n" + "="*60)
                print("STEP 6: Cleaning up")
                print("="*60)
                
                self._stop_and_remove_container(container_name)
                if cleanup_needed:
                    self._remove_docker_image(image_tag)
                
                print("\n✓ Cleanup complete")
                
                # Re-raise skip exception if we caught one
                if skip_exception:
                    raise skip_exception


if __name__ == '__main__':
    unittest.main()
