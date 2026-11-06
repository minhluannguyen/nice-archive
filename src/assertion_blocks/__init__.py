"""Assertion blocks for NixOS test framework."""

from .blocks import *

__all__ = [
    'assert_service_log_contains',
    'assert_root_privileges',
    'assert_screen_text',
    'assert_file_contains',
    'assert_file_exists',
    'assert_file_size_equals',
    'assert_cpu_usage_high',
    'assert_memory_usage_high',
    'assert_exact_execution_time',
    'assert_core_dump_exists'
]
