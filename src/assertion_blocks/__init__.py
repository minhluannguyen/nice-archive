"""Assertion blocks for NixOS test framework."""

from .blocks import *

__all__ = [
    'check_service_log_contains',
    'check_root_gid',
    'check_screen_text',
    'check_file_contains',
    'check_file_exists',
    'check_file_size_equals',
    'check_cpu_usage_high',
    'check_memory_usage_high',
    'check_exact_execution_time',
    'check_core_dump_exists'
]
