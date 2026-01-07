"""
Node-RED Integration Module for Flask API
Provides endpoints to monitor and manage Node-RED email automation
"""

import requests
import json
from datetime import datetime
import logging
from flask import jsonify, request

logger = logging.getLogger(__name__)

NODE_RED_BASE = "http://127.0.0.1:1880"
API_ENDPOINT = "/api"

class NodeRedManager:
    """Manager for Node-RED integration and monitoring"""
    
    @staticmethod
    def check_health():
        """Check if Node-RED is running and accessible"""
        try:
            response = requests.get(f"{NODE_RED_BASE}/", timeout=3)
            return {
                'status': 'healthy',
                'running': True,
                'url': NODE_RED_BASE,
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'unhealthy',
                'running': False,
                'url': NODE_RED_BASE,
                'message': 'Node-RED is not running',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'running': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def get_flows():
        """Get all Node-RED flows"""
        try:
            response = requests.get(f"{NODE_RED_BASE}/api/flows", timeout=5)
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'flows': response.json(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error getting Node-RED flows: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def get_debug_messages(limit=10):
        """Get recent debug messages from Node-RED"""
        try:
            response = requests.get(f"{NODE_RED_BASE}/api/debug?limit={limit}", timeout=5)
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'messages': response.json(),
                    'count': len(response.json()),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.warning(f"Could not retrieve debug messages: {str(e)}")
            return {
                'status': 'unavailable',
                'message': 'Debug endpoint not available',
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def trigger_daily_report():
        """Manually trigger daily report generation"""
        try:
            # Send request to Node-RED to trigger daily report
            payload = {'type': 'daily'}
            response = requests.post(
                f"{NODE_RED_BASE}/trigger/daily",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info("Daily report triggered via Node-RED")
                return {
                    'status': 'success',
                    'message': 'Daily report triggered',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error triggering daily report: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def trigger_weekly_report():
        """Manually trigger weekly report generation"""
        try:
            # Send request to Node-RED to trigger weekly report
            payload = {'type': 'weekly'}
            response = requests.post(
                f"{NODE_RED_BASE}/trigger/weekly",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info("Weekly report triggered via Node-RED")
                return {
                    'status': 'success',
                    'message': 'Weekly report triggered',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error triggering weekly report: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def get_email_history(limit=20):
        """Get history of sent emails"""
        try:
            response = requests.get(
                f"{NODE_RED_BASE}/api/emails?limit={limit}",
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'emails': response.json(),
                    'count': len(response.json()),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}',
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            logger.warning(f"Could not retrieve email history: {str(e)}")
            return {
                'status': 'unavailable',
                'message': 'Email history endpoint not available',
                'timestamp': datetime.now().isoformat()
            }


def setup_node_red_endpoints(app):
    """
    Register Node-RED management endpoints with Flask app
    
    Usage in api.py:
        from node_red_integration import setup_node_red_endpoints
        setup_node_red_endpoints(app)
    """
    
    @app.route('/api/node-red/status')
    def node_red_status():
        """Get Node-RED health status"""
        return jsonify(NodeRedManager.check_health()), 200
    
    @app.route('/api/node-red/flows')
    def node_red_flows():
        """Get Node-RED flows"""
        return jsonify(NodeRedManager.get_flows()), 200
    
    @app.route('/api/node-red/debug')
    def node_red_debug():
        """Get Node-RED debug messages"""
        limit = request.args.get('limit', 10, type=int)
        return jsonify(NodeRedManager.get_debug_messages(limit)), 200
    
    @app.route('/api/node-red/trigger-daily', methods=['POST'])
    def trigger_daily():
        """Manually trigger daily report"""
        return jsonify(NodeRedManager.trigger_daily_report()), 200
    
    @app.route('/api/node-red/trigger-weekly', methods=['POST'])
    def trigger_weekly():
        """Manually trigger weekly report"""
        return jsonify(NodeRedManager.trigger_weekly_report()), 200
    
    @app.route('/api/node-red/emails')
    def node_red_emails():
        """Get email history"""
        limit = request.args.get('limit', 20, type=int)
        return jsonify(NodeRedManager.get_email_history(limit)), 200
