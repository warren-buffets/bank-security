"""
Rules Engine with DSL evaluator.
Supports comparisons, logical operators, membership tests, and velocity functions.
"""
import re
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RuleDSLEvaluator:
    """
    DSL evaluator for rule expressions.
    
    Supported operators:
    - Comparisons: >, <, >=, <=, ==, !=
    - Logical: AND, OR, NOT
    - Membership: IN
    - Functions: velocity_24h(), velocity_1h()
    
    Example expressions:
    - "amount > 1000"
    - "amount > 1000 AND geo != user_home_geo"
    - "merchant_category IN ['gambling', 'crypto']"
    - "velocity_24h('amount') > 5000"
    """
    
    def __init__(self):
        self.operators = {
            '>': lambda a, b: self._safe_compare(a, b, lambda x, y: x > y),
            '<': lambda a, b: self._safe_compare(a, b, lambda x, y: x < y),
            '>=': lambda a, b: self._safe_compare(a, b, lambda x, y: x >= y),
            '<=': lambda a, b: self._safe_compare(a, b, lambda x, y: x <= y),
            '==': lambda a, b: self._safe_compare(a, b, lambda x, y: x == y),
            '!=': lambda a, b: self._safe_compare(a, b, lambda x, y: x != y),
        }
    
    def _safe_compare(self, a: Any, b: Any, op) -> bool:
        """Safely compare two values."""
        try:
            # Handle None values
            if a is None or b is None:
                if op.__name__ == '<lambda>':
                    # For == and !=
                    return a == b if '==' in str(op) else a != b
                return False
            
            # Convert types if needed
            if isinstance(a, (int, float)) and isinstance(b, str):
                try:
                    b = float(b)
                except (ValueError, TypeError):
                    return False
            elif isinstance(b, (int, float)) and isinstance(a, str):
                try:
                    a = float(a)
                except (ValueError, TypeError):
                    return False
            
            return op(a, b)
        except Exception as e:
            logger.warning(f"Comparison error: {e}")
            return False
    
    def _get_field_value(self, context: Dict[str, Any], field: str) -> Any:
        """Get field value from context, supporting nested fields."""
        try:
            # Support nested fields like metadata.key
            if '.' in field:
                parts = field.split('.')
                value = context
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        return None
                return value
            return context.get(field)
        except Exception as e:
            logger.warning(f"Error getting field {field}: {e}")
            return None
    
    def _evaluate_function(self, func_name: str, args: List[str], context: Dict[str, Any]) -> Any:
        """Evaluate built-in functions."""
        if func_name == 'velocity_24h':
            # Return pre-computed velocity or calculate
            if args and args[0] == 'amount':
                return context.get('amount_sum_24h', 0)
            elif args and args[0] == 'count':
                return context.get('tx_count_24h', 0)
            return context.get('tx_count_24h', 0)
        
        elif func_name == 'velocity_1h':
            if args and args[0] == 'count':
                return context.get('tx_count_1h', 0)
            return context.get('tx_count_1h', 0)
        
        return None
    
    def _parse_value(self, value_str: str) -> Any:
        """Parse a value from string."""
        value_str = value_str.strip()
        
        # Boolean
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        
        # None/null
        if value_str.lower() in ['none', 'null']:
            return None
        
        # String (quoted)
        if (value_str.startswith("'") and value_str.endswith("'")) or \
           (value_str.startswith('"') and value_str.endswith('"')):
            return value_str[1:-1]
        
        # Number
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass
        
        # List
        if value_str.startswith('[') and value_str.endswith(']'):
            list_str = value_str[1:-1]
            if not list_str.strip():
                return []
            items = [self._parse_value(item.strip()) for item in list_str.split(',')]
            return items
        
        # Return as string if can't parse
        return value_str
    
    def _evaluate_simple_expression(self, expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate a simple comparison expression."""
        expr = expr.strip()
        
        # Handle NOT operator
        if expr.upper().startswith('NOT '):
            return not self._evaluate_simple_expression(expr[4:].strip(), context)
        
        # Handle IN operator
        in_match = re.match(r'(\w+(?:\.\w+)*)\s+IN\s+(.+)', expr, re.IGNORECASE)
        if in_match:
            field = in_match.group(1)
            list_str = in_match.group(2)
            field_value = self._get_field_value(context, field)
            list_value = self._parse_value(list_str)
            if not isinstance(list_value, list):
                return False
            return field_value in list_value
        
        # Handle function calls
        func_match = re.match(r'(\w+)\(([^)]*)\)\s*(>|<|>=|<=|==|!=)\s*(.+)', expr)
        if func_match:
            func_name = func_match.group(1)
            func_args_str = func_match.group(2)
            operator = func_match.group(3)
            value_str = func_match.group(4)
            
            func_args = [arg.strip().strip("'\"") for arg in func_args_str.split(',')] if func_args_str else []
            func_result = self._evaluate_function(func_name, func_args, context)
            compare_value = self._parse_value(value_str)
            
            if func_result is None:
                return False
            
            return self.operators[operator](func_result, compare_value)
        
        # Handle standard comparisons
        for op in ['>=', '<=', '==', '!=', '>', '<']:
            if op in expr:
                parts = expr.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    
                    # Get left value (field or function)
                    left_value = self._get_field_value(context, left)
                    
                    # Get right value (field or literal)
                    if self._get_field_value(context, right) is not None:
                        right_value = self._get_field_value(context, right)
                    else:
                        right_value = self._parse_value(right)
                    
                    return self.operators[op](left_value, right_value)
        
        # If no operator found, treat as boolean field
        field_value = self._get_field_value(context, expr)
        return bool(field_value)
    
    def evaluate(self, expression: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a rule expression against a context.
        
        Args:
            expression: Rule expression in DSL format
            context: Transaction context dictionary
            
        Returns:
            True if rule matches, False otherwise
        """
        try:
            expression = expression.strip()
            
            if not expression:
                return False
            
            # Handle OR operator (lower precedence)
            if ' OR ' in expression.upper():
                parts = re.split(r'\s+OR\s+', expression, flags=re.IGNORECASE)
                return any(self.evaluate(part.strip(), context) for part in parts)
            
            # Handle AND operator (higher precedence)
            if ' AND ' in expression.upper():
                parts = re.split(r'\s+AND\s+', expression, flags=re.IGNORECASE)
                return all(self.evaluate(part.strip(), context) for part in parts)
            
            # Handle parentheses (future enhancement)
            if '(' in expression and ')' in expression and not re.match(r'\w+\(', expression):
                # This would need more sophisticated parsing
                # For now, treat as simple expression
                pass
            
            # Evaluate simple expression
            return self._evaluate_simple_expression(expression, context)
            
        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            return False
    
    def validate_expression(self, expression: str) -> tuple[bool, Optional[str]]:
        """
        Validate a rule expression syntax.
        
        Returns:
            (is_valid, error_message)
        """
        try:
            if not expression or not expression.strip():
                return False, "Expression cannot be empty"
            
            # Check for balanced quotes
            single_quotes = expression.count("'")
            double_quotes = expression.count('"')
            
            if single_quotes % 2 != 0:
                return False, "Unbalanced single quotes"
            if double_quotes % 2 != 0:
                return False, "Unbalanced double quotes"
            
            # Check for valid operators
            valid_pattern = r'^[a-zA-Z0-9_\.\s\(\)\[\],\'\"]+(?:(?:>|<|>=|<=|==|!=|AND|OR|NOT|IN)\s*[a-zA-Z0-9_\.\s\(\)\[\],\'\"]+)*$'
            
            # Basic syntax validation
            if re.search(r'(AND|OR)\s*(AND|OR)', expression, re.IGNORECASE):
                return False, "Consecutive logical operators"
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"


class RulesEngine:
    """Main rules engine that evaluates multiple rules."""
    
    def __init__(self):
        self.evaluator = RuleDSLEvaluator()
    
    def evaluate_rules(
        self,
        rules: List[Dict[str, Any]],
        context: Dict[str, Any],
        timeout_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple rules against a context.
        
        Args:
            rules: List of rule dictionaries
            context: Transaction context
            timeout_ms: Optional timeout in milliseconds
            
        Returns:
            List of matched rules with metadata
        """
        matched_rules = []
        start_time = datetime.utcnow()
        
        # Sort rules by priority (higher first)
        sorted_rules = sorted(rules, key=lambda r: r.get('priority', 0), reverse=True)
        
        for rule in sorted_rules:
            # Check timeout
            if timeout_ms:
                elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                if elapsed_ms > timeout_ms:
                    logger.warning(f"Rule evaluation timeout after {elapsed_ms}ms")
                    break
            
            # Skip disabled rules
            if not rule.get('enabled', True):
                continue
            
            try:
                expression = rule.get('expression', '')
                if self.evaluator.evaluate(expression, context):
                    matched_rules.append({
                        'rule_id': rule.get('id'),
                        'rule_name': rule.get('name'),
                        'expression': expression,
                        'action': rule.get('action', 'review'),
                        'reason': rule.get('description', f"Rule {rule.get('name')} matched"),
                        'priority': rule.get('priority', 0),
                        'metadata': rule.get('metadata', {})
                    })
                    
                    # If action is deny, we might want to stop early (fail-fast)
                    if rule.get('action') == 'deny':
                        logger.info(f"Deny rule matched: {rule.get('name')}")
                        # Could break here for fail-fast, but continue to collect all matches
                        
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.get('id')}: {e}")
                continue
        
        return matched_rules
