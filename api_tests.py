"""
API Testing and Quality Assurance Script
Validates all API endpoints and data quality
"""

import requests
import time
import json
from typing import Dict, Any, List
import sys

# Base URL for API
BASE_URL = "http://127.0.0.1:5001"

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.ENDC}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")


class APITester:
    """Test all API endpoints and data quality"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.tests_passed = 0
        self.tests_failed = 0
        self.warnings = 0
    
    def test_endpoint(
        self,
        endpoint: str,
        expected_status: int = 200,
        expected_keys: List[str] = None,
        max_response_time: float = 5.0
    ) -> bool:
        """
        Test an API endpoint
        
        Args:
            endpoint: API endpoint path (e.g., '/api/flights/all')
            expected_status: Expected HTTP status code
            expected_keys: Expected keys in JSON response
            max_response_time: Maximum acceptable response time in seconds
            
        Returns:
            True if test passed, False otherwise
        """
        url = f"{self.base_url}{endpoint}"
        print_info(f"Testing: {endpoint}")
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            response_time = time.time() - start_time
            
            # Check status code
            if response.status_code != expected_status:
                print_error(f"Expected status {expected_status}, got {response.status_code}")
                self.tests_failed += 1
                return False
            
            # Check response time
            if response_time > max_response_time:
                print_warning(f"Slow response: {response_time:.2f}s (max: {max_response_time}s)")
                self.warnings += 1
            else:
                print_success(f"Response time: {response_time:.2f}s")
            
            # Parse JSON
            try:
                data = response.json()
            except json.JSONDecodeError:
                print_error("Invalid JSON response")
                self.tests_failed += 1
                return False
            
            # Check expected keys
            if expected_keys:
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    print_error(f"Missing keys: {missing_keys}")
                    self.tests_failed += 1
                    return False
                print_success(f"All expected keys present: {expected_keys}")
            
            # Additional data validation
            if 'error' in data and data['error']:
                print_warning(f"API returned error: {data.get('message', 'Unknown error')}")
                self.warnings += 1
            
            self.tests_passed += 1
            return True
            
        except requests.exceptions.Timeout:
            print_error(f"Request timeout (>{10}s)")
            self.tests_failed += 1
            return False
        except requests.exceptions.ConnectionError:
            print_error("Connection error - is the server running?")
            self.tests_failed += 1
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            self.tests_failed += 1
            return False
    
    def test_flight_data_quality(self):
        """Test flight data quality and airline filtering"""
        print_header("Flight Data Quality Tests")
        
        url = f"{self.base_url}/api/flights/all"
        try:
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'flights' not in data:
                print_error("No 'flights' key in response")
                return False
            
            flights = data['flights']
            print_info(f"Found {len(flights)} flights")
            
            # Real ICT airlines whitelist
            real_ict_airlines = {
                'Allegiant Air', 'American Airlines', 'Delta Air Lines',
                'Southwest Airlines', 'United Airlines', 'Alpine Air Express'
            }
            
            # Check each flight
            invalid_airlines = set()
            for flight in flights:
                airline = flight.get('Airline', '')
                if airline and airline not in real_ict_airlines:
                    invalid_airlines.add(airline)
            
            if invalid_airlines:
                print_error(f"Found flights from non-ICT airlines: {invalid_airlines}")
                print_error("Airline filtering NOT working correctly!")
                self.tests_failed += 1
                return False
            else:
                print_success("All flights from real ICT operators only")
                print_success(f"Valid airlines: {real_ict_airlines}")
                self.tests_passed += 1
                return True
                
        except Exception as e:
            print_error(f"Flight data quality test failed: {e}")
            self.tests_failed += 1
            return False
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print_header("ICT Airport API - Quality Assurance Tests")
        
        # Test core flight endpoints
        print_header("Flight Endpoints")
        self.test_endpoint('/api/flights/all', expected_keys=['flights', 'count', 'timestamp'])
        self.test_endpoint('/api/flights', expected_keys=['flights'])
        self.test_endpoint('/api/flights/flightradar24', expected_keys=['flights', 'source'])
        
        # Test flight data quality
        self.test_flight_data_quality()
        
        # Test weather endpoint
        print_header("Weather Endpoint")
        self.test_endpoint('/api/weather', expected_keys=['weather'])
        
        # Test predictions endpoint
        print_header("Predictions Endpoint")
        self.test_endpoint('/api/predictions/all', expected_keys=['predictions'])
        
        # Test statistics endpoints
        print_header("Statistics Endpoints")
        self.test_endpoint('/api/operations/today', expected_keys=['date', 'operations', 'summary'])
        
        # Note: /api/statistics/airlines endpoint does not exist - only /api/statistics/bts
        # Skipping to avoid false failures
        
        # Test disabled endpoints (should return 410)
        print_header("Disabled Endpoints (Expected 410)")
        self.test_endpoint('/api/flights/airportia', expected_status=410)
        
        # Print summary
        print_header("Test Summary")
        total_tests = self.tests_passed + self.tests_failed
        print(f"Total Tests: {total_tests}")
        print_success(f"Passed: {self.tests_passed}")
        if self.tests_failed > 0:
            print_error(f"Failed: {self.tests_failed}")
        if self.warnings > 0:
            print_warning(f"Warnings: {self.warnings}")
        
        # Calculate success rate
        if total_tests > 0:
            success_rate = (self.tests_passed / total_tests) * 100
            if success_rate == 100:
                print_success(f"\n🎉 All tests passed! Success rate: {success_rate:.1f}%")
            elif success_rate >= 80:
                print_warning(f"\n⚠ Most tests passed. Success rate: {success_rate:.1f}%")
            else:
                print_error(f"\n❌ Many tests failed. Success rate: {success_rate:.1f}%")
        
        return self.tests_failed == 0


def main():
    """Main test execution"""
    tester = APITester()
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
