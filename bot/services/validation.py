# ------------------- Файл services/validation.py -------------------
from datetime import datetime

class DataValidator:
    @staticmethod
    def validate_field(field_name: str, field_type: str, value: str):
        """Валидация значения поля по типу"""
        try:
            if field_type.startswith('INTEGER'):
                return int(value)
            elif field_type.startswith('VARCHAR'):
                if not value.strip():
                    raise ValueError("Не может быть пустым")
                return value.strip()
            elif field_type.startswith('DATETIME'):
                return datetime.strptime(value, "%d.%m.%Y %H:%M")
            elif field_type.startswith('BOOLEAN'):
                return value.lower() in ('true', '1', 'да')
            return value
        except ValueError as e:
            raise ValueError(f"Некорректное значение для {field_name}: {str(e)}")