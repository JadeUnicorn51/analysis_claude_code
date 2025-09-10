"""
参数验证工具
"""

from typing import Any, Dict, List, Optional, Union
import re
from pathlib import Path


class ValidationError(Exception):
    """验证错误异常"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class ParameterValidator:
    """参数验证器"""
    
    @staticmethod
    def validate_string(
        value: Any,
        field_name: str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        allowed_values: Optional[List[str]] = None,
        required: bool = True
    ) -> str:
        """
        验证字符串参数
        
        Args:
            value: 待验证的值
            field_name: 字段名称
            min_length: 最小长度
            max_length: 最大长度
            pattern: 正则表达式模式
            allowed_values: 允许的值列表
            required: 是否必需
            
        Returns:
            str: 验证后的字符串
            
        Raises:
            ValidationError: 验证失败
        """
        if value is None:
            if required:
                raise ValidationError(f"字段 {field_name} 是必需的", field_name, value)
            return ""
        
        if not isinstance(value, str):
            raise ValidationError(f"字段 {field_name} 必须是字符串", field_name, value)
        
        if min_length is not None and len(value) < min_length:
            raise ValidationError(
                f"字段 {field_name} 长度不能少于 {min_length} 个字符",
                field_name, value
            )
        
        if max_length is not None and len(value) > max_length:
            raise ValidationError(
                f"字段 {field_name} 长度不能超过 {max_length} 个字符",
                field_name, value
            )
        
        if pattern and not re.match(pattern, value):
            raise ValidationError(
                f"字段 {field_name} 格式不正确",
                field_name, value
            )
        
        if allowed_values and value not in allowed_values:
            raise ValidationError(
                f"字段 {field_name} 必须是以下值之一: {', '.join(allowed_values)}",
                field_name, value
            )
        
        return value
    
    @staticmethod
    def validate_integer(
        value: Any,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = True
    ) -> int:
        """
        验证整数参数
        
        Args:
            value: 待验证的值
            field_name: 字段名称
            min_value: 最小值
            max_value: 最大值
            required: 是否必需
            
        Returns:
            int: 验证后的整数
            
        Raises:
            ValidationError: 验证失败
        """
        if value is None:
            if required:
                raise ValidationError(f"字段 {field_name} 是必需的", field_name, value)
            return 0
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"字段 {field_name} 必须是整数", field_name, value)
        
        if min_value is not None and int_value < min_value:
            raise ValidationError(
                f"字段 {field_name} 不能小于 {min_value}",
                field_name, value
            )
        
        if max_value is not None and int_value > max_value:
            raise ValidationError(
                f"字段 {field_name} 不能大于 {max_value}",
                field_name, value
            )
        
        return int_value
    
    @staticmethod
    def validate_float(
        value: Any,
        field_name: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        required: bool = True
    ) -> float:
        """
        验证浮点数参数
        
        Args:
            value: 待验证的值
            field_name: 字段名称
            min_value: 最小值
            max_value: 最大值
            required: 是否必需
            
        Returns:
            float: 验证后的浮点数
            
        Raises:
            ValidationError: 验证失败
        """
        if value is None:
            if required:
                raise ValidationError(f"字段 {field_name} 是必需的", field_name, value)
            return 0.0
        
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"字段 {field_name} 必须是数字", field_name, value)
        
        if min_value is not None and float_value < min_value:
            raise ValidationError(
                f"字段 {field_name} 不能小于 {min_value}",
                field_name, value
            )
        
        if max_value is not None and float_value > max_value:
            raise ValidationError(
                f"字段 {field_name} 不能大于 {max_value}",
                field_name, value
            )
        
        return float_value
    
    @staticmethod
    def validate_boolean(
        value: Any,
        field_name: str,
        required: bool = True
    ) -> bool:
        """
        验证布尔参数
        
        Args:
            value: 待验证的值
            field_name: 字段名称
            required: 是否必需
            
        Returns:
            bool: 验证后的布尔值
            
        Raises:
            ValidationError: 验证失败
        """
        if value is None:
            if required:
                raise ValidationError(f"字段 {field_name} 是必需的", field_name, value)
            return False
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ('true', '1', 'yes', 'on'):
                return True
            elif value_lower in ('false', '0', 'no', 'off'):
                return False
        
        raise ValidationError(f"字段 {field_name} 必须是布尔值", field_name, value)
    
    @staticmethod
    def validate_list(
        value: Any,
        field_name: str,
        item_type: type = str,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        required: bool = True
    ) -> List[Any]:
        """
        验证列表参数
        
        Args:
            value: 待验证的值
            field_name: 字段名称
            item_type: 列表项类型
            min_length: 最小长度
            max_length: 最大长度
            required: 是否必需
            
        Returns:
            List[Any]: 验证后的列表
            
        Raises:
            ValidationError: 验证失败
        """
        if value is None:
            if required:
                raise ValidationError(f"字段 {field_name} 是必需的", field_name, value)
            return []
        
        if not isinstance(value, list):
            raise ValidationError(f"字段 {field_name} 必须是列表", field_name, value)
        
        if min_length is not None and len(value) < min_length:
            raise ValidationError(
                f"字段 {field_name} 长度不能少于 {min_length} 项",
                field_name, value
            )
        
        if max_length is not None and len(value) > max_length:
            raise ValidationError(
                f"字段 {field_name} 长度不能超过 {max_length} 项",
                field_name, value
            )
        
        # 验证列表项类型
        for i, item in enumerate(value):
            if not isinstance(item, item_type):
                raise ValidationError(
                    f"字段 {field_name}[{i}] 必须是 {item_type.__name__} 类型",
                    field_name, value
                )
        
        return value
    
    @staticmethod
    def validate_dict(
        value: Any,
        field_name: str,
        required_keys: Optional[List[str]] = None,
        allowed_keys: Optional[List[str]] = None,
        required: bool = True
    ) -> Dict[str, Any]:
        """
        验证字典参数
        
        Args:
            value: 待验证的值
            field_name: 字段名称
            required_keys: 必需的键列表
            allowed_keys: 允许的键列表
            required: 是否必需
            
        Returns:
            Dict[str, Any]: 验证后的字典
            
        Raises:
            ValidationError: 验证失败
        """
        if value is None:
            if required:
                raise ValidationError(f"字段 {field_name} 是必需的", field_name, value)
            return {}
        
        if not isinstance(value, dict):
            raise ValidationError(f"字段 {field_name} 必须是字典", field_name, value)
        
        # 检查必需的键
        if required_keys:
            for key in required_keys:
                if key not in value:
                    raise ValidationError(
                        f"字段 {field_name} 缺少必需的键: {key}",
                        field_name, value
                    )
        
        # 检查允许的键
        if allowed_keys:
            for key in value.keys():
                if key not in allowed_keys:
                    raise ValidationError(
                        f"字段 {field_name} 包含不允许的键: {key}",
                        field_name, value
                    )
        
        return value
    
    @staticmethod
    def validate_file_path(
        value: Any,
        field_name: str,
        must_exist: bool = False,
        allowed_extensions: Optional[List[str]] = None,
        required: bool = True
    ) -> str:
        """
        验证文件路径参数
        
        Args:
            value: 待验证的值
            field_name: 字段名称
            must_exist: 文件是否必须存在
            allowed_extensions: 允许的文件扩展名
            required: 是否必需
            
        Returns:
            str: 验证后的文件路径
            
        Raises:
            ValidationError: 验证失败
        """
        if value is None:
            if required:
                raise ValidationError(f"字段 {field_name} 是必需的", field_name, value)
            return ""
        
        if not isinstance(value, str):
            raise ValidationError(f"字段 {field_name} 必须是字符串", field_name, value)
        
        try:
            path = Path(value)
        except Exception:
            raise ValidationError(f"字段 {field_name} 不是有效的路径", field_name, value)
        
        if must_exist and not path.exists():
            raise ValidationError(f"文件不存在: {value}", field_name, value)
        
        if allowed_extensions:
            if path.suffix.lower() not in [ext.lower() for ext in allowed_extensions]:
                raise ValidationError(
                    f"字段 {field_name} 文件扩展名必须是: {', '.join(allowed_extensions)}",
                    field_name, value
                )
        
        return str(path)


def validate_parameters(
    parameters: Dict[str, Any],
    validation_schema: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    根据schema验证参数
    
    Args:
        parameters: 待验证的参数
        validation_schema: 验证schema
        
    Returns:
        Dict[str, Any]: 验证后的参数
        
    Raises:
        ValidationError: 验证失败
    """
    validated_params = {}
    
    for field_name, field_schema in validation_schema.items():
        field_type = field_schema.get('type', 'string')
        value = parameters.get(field_name)
        
        validator = ParameterValidator()
        
        if field_type == 'string':
            validated_params[field_name] = validator.validate_string(
                value, field_name, **field_schema
            )
        elif field_type == 'integer':
            validated_params[field_name] = validator.validate_integer(
                value, field_name, **field_schema
            )
        elif field_type == 'float':
            validated_params[field_name] = validator.validate_float(
                value, field_name, **field_schema
            )
        elif field_type == 'boolean':
            validated_params[field_name] = validator.validate_boolean(
                value, field_name, **field_schema
            )
        elif field_type == 'list':
            validated_params[field_name] = validator.validate_list(
                value, field_name, **field_schema
            )
        elif field_type == 'dict':
            validated_params[field_name] = validator.validate_dict(
                value, field_name, **field_schema
            )
        elif field_type == 'file_path':
            validated_params[field_name] = validator.validate_file_path(
                value, field_name, **field_schema
            )
        else:
            # 未知类型，直接返回原值
            validated_params[field_name] = value
    
    return validated_params
