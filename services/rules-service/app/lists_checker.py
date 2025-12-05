"""
Deny/Allow Lists Checker using Redis cache.
"""
import logging
from typing import Dict, List, Optional, Set
import redis.asyncio as redis
from datetime import datetime

logger = logging.getLogger(__name__)


class ListsChecker:
    """
    Checks transaction context against deny/allow lists stored in Redis.
    
    Redis key structure:
    - deny_list:user_id - Set of denied user IDs
    - deny_list:ip_address - Set of denied IP addresses
    - deny_list:device_id - Set of denied device IDs
    - deny_list:merchant_id - Set of denied merchant IDs
    - allow_list:user_id - Set of allowed/whitelisted user IDs
    - allow_list:ip_address - Set of allowed IP addresses
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
        # Fields to check against lists
        self.check_fields = [
            'user_id',
            'ip_address',
            'device_id',
            'merchant_id',
            'geo'
        ]
    
    async def check_deny_lists(self, context: Dict) -> List[Dict]:
        """
        Check if any context fields are in deny lists.
        
        Args:
            context: Transaction context dictionary
            
        Returns:
            List of deny list matches
        """
        matches = []
        
        try:
            for field in self.check_fields:
                value = context.get(field)
                if not value:
                    continue
                
                key = f"deny_list:{field}"
                
                # Check if value is in deny list
                is_denied = await self.redis.sismember(key, str(value))
                
                if is_denied:
                    matches.append({
                        'list_type': 'deny',
                        'list_name': key,
                        'matched_value': str(value),
                        'field': field,
                        'reason': f"{field} '{value}' is on deny list"
                    })
                    logger.info(f"Deny list match: {field}={value}")
        
        except Exception as e:
            logger.error(f"Error checking deny lists: {e}")
        
        return matches
    
    async def check_allow_lists(self, context: Dict) -> List[Dict]:
        """
        Check if any context fields are in allow lists.
        
        Args:
            context: Transaction context dictionary
            
        Returns:
            List of allow list matches
        """
        matches = []
        
        try:
            for field in self.check_fields:
                value = context.get(field)
                if not value:
                    continue
                
                key = f"allow_list:{field}"
                
                # Check if value is in allow list
                is_allowed = await self.redis.sismember(key, str(value))
                
                if is_allowed:
                    matches.append({
                        'list_type': 'allow',
                        'list_name': key,
                        'matched_value': str(value),
                        'field': field,
                        'reason': f"{field} '{value}' is on allow list"
                    })
                    logger.info(f"Allow list match: {field}={value}")
        
        except Exception as e:
            logger.error(f"Error checking allow lists: {e}")
        
        return matches
    
    async def check_all_lists(self, context: Dict) -> tuple[List[Dict], List[Dict]]:
        """
        Check both deny and allow lists.
        
        Args:
            context: Transaction context dictionary
            
        Returns:
            (deny_matches, allow_matches)
        """
        deny_matches = await self.check_deny_lists(context)
        allow_matches = await self.check_allow_lists(context)
        
        return deny_matches, allow_matches
    
    async def add_to_deny_list(self, field: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Add a value to a deny list.
        
        Args:
            field: Field name (e.g., 'user_id', 'ip_address')
            value: Value to deny
            ttl: Optional TTL in seconds
            
        Returns:
            True if added successfully
        """
        try:
            key = f"deny_list:{field}"
            await self.redis.sadd(key, str(value))
            
            if ttl:
                await self.redis.expire(key, ttl)
            
            logger.info(f"Added {value} to {key}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding to deny list: {e}")
            return False
    
    async def add_to_allow_list(self, field: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Add a value to an allow list.
        
        Args:
            field: Field name (e.g., 'user_id', 'ip_address')
            value: Value to allow
            ttl: Optional TTL in seconds
            
        Returns:
            True if added successfully
        """
        try:
            key = f"allow_list:{field}"
            await self.redis.sadd(key, str(value))
            
            if ttl:
                await self.redis.expire(key, ttl)
            
            logger.info(f"Added {value} to {key}")
            return True
        
        except Exception as e:
            logger.error(f"Error adding to allow list: {e}")
            return False
    
    async def remove_from_deny_list(self, field: str, value: str) -> bool:
        """Remove a value from a deny list."""
        try:
            key = f"deny_list:{field}"
            await self.redis.srem(key, str(value))
            logger.info(f"Removed {value} from {key}")
            return True
        except Exception as e:
            logger.error(f"Error removing from deny list: {e}")
            return False
    
    async def remove_from_allow_list(self, field: str, value: str) -> bool:
        """Remove a value from an allow list."""
        try:
            key = f"allow_list:{field}"
            await self.redis.srem(key, str(value))
            logger.info(f"Removed {value} from {key}")
            return True
        except Exception as e:
            logger.error(f"Error removing from allow list: {e}")
            return False
    
    async def get_list_members(self, list_type: str, field: str) -> Set[str]:
        """
        Get all members of a list.
        
        Args:
            list_type: 'deny' or 'allow'
            field: Field name
            
        Returns:
            Set of values in the list
        """
        try:
            key = f"{list_type}_list:{field}"
            members = await self.redis.smembers(key)
            return {m.decode() if isinstance(m, bytes) else m for m in members}
        except Exception as e:
            logger.error(f"Error getting list members: {e}")
            return set()
    
    async def clear_list(self, list_type: str, field: str) -> bool:
        """Clear all entries from a list."""
        try:
            key = f"{list_type}_list:{field}"
            await self.redis.delete(key)
            logger.info(f"Cleared {key}")
            return True
        except Exception as e:
            logger.error(f"Error clearing list: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
