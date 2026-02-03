"""Configuration constants for snapshot system.

This module centralizes all magic numbers and configuration values used
throughout the snapshot system for easier maintenance and customization.
"""

# Snapshot size management
DEFAULT_SIZE_WARNING_MB = 500
"""Warn user when snapshot exceeds this size (0 to disable)."""

DEFAULT_CLEANUP_AGE_DAYS = 7
"""Default age threshold for automatic cleanup."""

MAX_SNAPSHOT_AGE_DAYS = 30
"""Hard limit - snapshots older than this are always cleaned."""

# Display settings
USER_QUESTION_MAX_LENGTH = 150
"""Maximum length for user question in snapshot metadata."""

PREVIEW_FILE_DISPLAY_LIMIT = 15
"""Number of files to show in preview before truncating."""

# Emergency backup
EMERGENCY_BACKUP_PREFIX = ".emergency-backup-"
"""Prefix for emergency backup directories."""

# Storage paths
SNAPSHOT_DIR_NAME = "message-data"  #### KK-code altercation: renamed from "snapshots"
"""Directory name for message data storage."""

SESSION_LOG_DIR_NAME = "logs/session"
"""Directory name for session logs."""

KKCODE_DIR_NAME = ".kkcode"
"""Root directory name for all KK-code project-local data."""

# Diff management (from config.py)
DEFAULT_DIFF_CLEANUP_DELAY = 300
"""Default delay in seconds before cleaning up diff files (5 minutes)."""
