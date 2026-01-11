"""
Container Lifecycle Manager

Manages Docker containers, handles CPU usage issues, and auto-restarts containers.
"""

import docker
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psutil

logger = logging.getLogger(__name__)


class ContainerLifecycleManager:
    """Manages container lifecycle and resource usage"""

    def __init__(self):
        """Initialize container manager"""
        try:
            self.client = docker.from_env()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.client = None

        self.cpu_threshold = 80.0  # CPU usage percentage
        self.memory_threshold = 85.0  # Memory usage percentage
        self.restart_cooldown = 300  # 5 minutes cooldown

        self.restart_history = {}

    def monitor_containers(self) -> List[Dict[str, Any]]:
        """
        Monitor all containers for resource issues

        Returns:
            List of container status reports
        """
        if not self.client:
            return []

        logger.info("Monitoring containers")

        reports = []

        try:
            containers = self.client.containers.list()

            for container in containers:
                report = self._check_container_health(container)
                reports.append(report)

                # Auto-remediate if needed
                if report['needs_restart']:
                    self._auto_restart_container(container, report['reason'])

        except Exception as e:
            logger.error(f"Container monitoring failed: {e}")

        return reports

    def _check_container_health(self, container: docker.models.containers.Container) -> Dict[str, Any]:
        """Check container health and resource usage"""
        report = {
            'container_id': container.id[:12],
            'name': container.name,
            'status': container.status,
            'image': container.image.tags[0] if container.image.tags else 'unknown',
            'cpu_usage': 0.0,
            'memory_usage': 0.0,
            'needs_restart': False,
            'reason': ''
        }

        try:
            # Get container stats
            stats = container.stats(stream=False)

            # Calculate CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_count = stats['cpu_stats']['online_cpus']

            if system_delta > 0:
                cpu_usage = (cpu_delta / system_delta) * cpu_count * 100.0
                report['cpu_usage'] = round(cpu_usage, 2)

            # Calculate memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_percent = (memory_usage / memory_limit) * 100.0
            report['memory_usage'] = round(memory_percent, 2)

            # Check thresholds
            if report['cpu_usage'] > self.cpu_threshold:
                report['needs_restart'] = True
                report['reason'] = f"High CPU usage: {report['cpu_usage']}%"

            if report['memory_usage'] > self.memory_threshold:
                report['needs_restart'] = True
                report['reason'] = f"High memory usage: {report['memory_usage']}%"

            # Check if container is unhealthy
            health = container.attrs.get('State', {}).get('Health', {})
            if health.get('Status') == 'unhealthy':
                report['needs_restart'] = True
                report['reason'] = 'Container unhealthy'

        except Exception as e:
            logger.error(f"Error checking container {container.name}: {e}")
            report['reason'] = f"Monitoring error: {e}"

        return report

    def _auto_restart_container(self, container: docker.models.containers.Container, reason: str):
        """Auto-restart container with cooldown"""
        container_id = container.id[:12]

        # Check cooldown
        last_restart = self.restart_history.get(container_id)
        if last_restart:
            time_since_restart = (datetime.now() - last_restart).total_seconds()
            if time_since_restart < self.restart_cooldown:
                logger.info(f"Skipping restart for {container.name} (cooldown)")
                return

        logger.info(f"Auto-restarting container {container.name}: {reason}")

        try:
            container.restart(timeout=10)
            self.restart_history[container_id] = datetime.now()
            logger.info(f"Container {container.name} restarted successfully")

        except Exception as e:
            logger.error(f"Failed to restart container {container.name}: {e}")

    def restart_containers(self, pattern: str) -> Dict[str, Any]:
        """
        Restart containers matching pattern

        Args:
            pattern: Pattern to match container names

        Returns:
            Restart result
        """
        if not self.client:
            return {'count': 0, 'message': 'Docker not available'}

        logger.info(f"Restarting containers matching: {pattern}")

        result = {
            'count': 0,
            'restarted': [],
            'failed': []
        }

        try:
            containers = self.client.containers.list()

            for container in containers:
                if pattern in container.name or pattern == '*':
                    try:
                        container.restart(timeout=10)
                        result['count'] += 1
                        result['restarted'].append(container.name)
                        logger.info(f"Restarted: {container.name}")
                    except Exception as e:
                        result['failed'].append({
                            'name': container.name,
                            'error': str(e)
                        })
                        logger.error(f"Failed to restart {container.name}: {e}")

        except Exception as e:
            logger.error(f"Container restart operation failed: {e}")

        return result

    def stop_overused_containers(self) -> Dict[str, Any]:
        """
        Stop containers exceeding resource thresholds

        Returns:
            Operation result
        """
        logger.info("Stopping overused containers")

        result = {
            'count': 0,
            'stopped': [],
            'reason': []
        }

        reports = self.monitor_containers()

        for report in reports:
            if report['needs_restart']:
                try:
                    container = self.client.containers.get(report['container_id'])
                    container.stop(timeout=10)

                    result['count'] += 1
                    result['stopped'].append(report['name'])
                    result['reason'].append(report['reason'])

                    logger.info(f"Stopped {report['name']}: {report['reason']}")

                except Exception as e:
                    logger.error(f"Failed to stop {report['name']}: {e}")

        return result

    def deploy_fresh_containers(self, image_name: str, count: int = 1) -> Dict[str, Any]:
        """
        Deploy fresh containers from image

        Args:
            image_name: Docker image to deploy
            count: Number of containers to deploy

        Returns:
            Deployment result
        """
        if not self.client:
            return {'count': 0, 'message': 'Docker not available'}

        logger.info(f"Deploying {count} fresh containers from {image_name}")

        result = {
            'count': 0,
            'deployed': [],
            'failed': []
        }

        try:
            # Pull latest image
            logger.info(f"Pulling image: {image_name}")
            self.client.images.pull(image_name)

            # Deploy containers
            for i in range(count):
                try:
                    container_name = f"{image_name.split(':')[0]}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}"

                    container = self.client.containers.run(
                        image_name,
                        name=container_name,
                        detach=True,
                        restart_policy={'Name': 'unless-stopped'}
                    )

                    result['count'] += 1
                    result['deployed'].append({
                        'id': container.id[:12],
                        'name': container_name
                    })

                    logger.info(f"Deployed: {container_name}")

                except Exception as e:
                    result['failed'].append({
                        'index': i,
                        'error': str(e)
                    })
                    logger.error(f"Failed to deploy container {i}: {e}")

        except Exception as e:
            logger.error(f"Image pull/deployment failed: {e}")
            result['message'] = str(e)

        return result

    def cleanup_old_images(self, days_old: int = 7) -> Dict[str, Any]:
        """
        Remove old unused images

        Args:
            days_old: Remove images older than this many days

        Returns:
            Cleanup result
        """
        if not self.client:
            return {'count': 0, 'message': 'Docker not available'}

        logger.info(f"Cleaning up images older than {days_old} days")

        result = {
            'count': 0,
            'removed': [],
            'space_freed': 0
        }

        try:
            images = self.client.images.list()
            cutoff_date = datetime.now() - timedelta(days=days_old)

            for image in images:
                # Skip images in use
                if image.tags and self._image_in_use(image):
                    continue

                # Check age
                created_at = datetime.fromisoformat(image.attrs['Created'].replace('Z', '+00:00'))

                if created_at < cutoff_date:
                    try:
                        image_id = image.id[:12]
                        size = image.attrs['Size']

                        self.client.images.remove(image.id, force=True)

                        result['count'] += 1
                        result['removed'].append(image_id)
                        result['space_freed'] += size

                        logger.info(f"Removed image: {image_id}")

                    except Exception as e:
                        logger.warning(f"Failed to remove image {image.id}: {e}")

        except Exception as e:
            logger.error(f"Image cleanup failed: {e}")

        # Convert bytes to MB
        result['space_freed_mb'] = round(result['space_freed'] / (1024 * 1024), 2)

        return result

    def _image_in_use(self, image: docker.models.images.Image) -> bool:
        """Check if image is in use by any container"""
        try:
            containers = self.client.containers.list(all=True)

            for container in containers:
                if container.image.id == image.id:
                    return True

            return False

        except Exception:
            return True  # Assume in use if check fails

    def get_system_resources(self) -> Dict[str, Any]:
        """Get system resource usage"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'timestamp': datetime.now().isoformat()
        }
