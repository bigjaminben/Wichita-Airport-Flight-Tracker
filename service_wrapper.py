"""
Windows Service Wrapper for ICT Flight Tracker
Runs the flight tracker as a Windows Service for 24/7 operation
"""
import sys
import time
import logging
from pathlib import Path
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import subprocess
import os

# Setup logging
LOG_DIR = Path(__file__).parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FlightTrackerService')


class FlightTrackerService(win32serviceutil.ServiceFramework):
    _svc_name_ = 'ICTFlightTracker'
    _svc_display_name_ = 'ICT Flight Tracker Dashboard'
    _svc_description_ = 'Wichita Airport Flight Tracker - Deloitte Dashboard (24/7 Service)'
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.process = None
        socket.setdefaulttimeout(60)
        
        # Get the directory where the service is running
        self.service_dir = Path(__file__).parent
        self.python_exe = self.service_dir / '.venv' / 'Scripts' / 'python.exe'
        self.server_script = self.service_dir / 'serve_prod.py'
        
        logger.info(f'Service initialized - Directory: {self.service_dir}')
        logger.info(f'Python: {self.python_exe}')
        logger.info(f'Server script: {self.server_script}')
    
    def SvcStop(self):
        """Called when the service is requested to stop"""
        logger.info('Service stop requested')
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False
        
        # Terminate the server process
        if self.process:
            try:
                logger.info('Terminating server process')
                self.process.terminate()
                self.process.wait(timeout=10)
                logger.info('Server process terminated successfully')
            except Exception as e:
                logger.error(f'Error terminating server: {e}')
                try:
                    self.process.kill()
                except:
                    pass
    
    def SvcDoRun(self):
        """Called when the service is started"""
        logger.info('Service starting...')
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.main()
        except Exception as e:
            logger.error(f'Service error: {e}', exc_info=True)
            servicemanager.LogErrorMsg(f'Service error: {e}')
    
    def main(self):
        """Main service loop - keeps the server running"""
        logger.info('Starting main service loop')
        
        restart_delay = 5  # Seconds to wait before restarting on failure
        
        while self.running:
            try:
                # Start the Flask server
                logger.info('Starting Flask server process')
                
                self.process = subprocess.Popen(
                    [str(self.python_exe), str(self.server_script)],
                    cwd=str(self.service_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                logger.info(f'Server process started with PID: {self.process.pid}')
                
                # Monitor the process
                while self.running:
                    # Check if service stop was requested
                    rc = win32event.WaitForSingleObject(self.stop_event, 1000)
                    if rc == win32event.WAIT_OBJECT_0:
                        logger.info('Stop event received')
                        break
                    
                    # Check if server process is still running
                    if self.process.poll() is not None:
                        logger.warning(f'Server process exited with code: {self.process.returncode}')
                        
                        # Log any output
                        stdout, stderr = self.process.communicate(timeout=1)
                        if stdout:
                            logger.info(f'Server stdout: {stdout.decode()}')
                        if stderr:
                            logger.error(f'Server stderr: {stderr.decode()}')
                        
                        if self.running:
                            logger.info(f'Restarting server in {restart_delay} seconds...')
                            time.sleep(restart_delay)
                            break  # Break inner loop to restart
                        else:
                            break
                
                if not self.running:
                    break
                    
            except Exception as e:
                logger.error(f'Error in service loop: {e}', exc_info=True)
                if self.running:
                    logger.info(f'Retrying in {restart_delay} seconds...')
                    time.sleep(restart_delay)
        
        logger.info('Service stopped')


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FlightTrackerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(FlightTrackerService)
