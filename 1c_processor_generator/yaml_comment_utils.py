"""
YAML Comment Preservation Utilities

This module provides helper functions for modifying YAML structures while preserving
comments, formatting, and blank lines. Designed for v2.30.0 - Incremental YAML Updates.

Key Features:
- Preserve inline comments (key: value  # comment)
- Preserve block comments (above sections)
- Preserve blank lines for readability
- Work with ruamel.yaml's CommentedMap and CommentedSeq

Technical Background:
- ruamel.yaml preserves comments by default when using CommentedMap/CommentedSeq
- PROBLEM: Direct dict assignment (obj[key] = value) loses comment attachment
- SOLUTION: Extract comments before modification, restore after

Author: 1C Processor Generator Team
Version: 2.30.0
Date: 2025-11-20
"""

import logging
from typing import Any, Optional, Union, List
from ruamel.yaml.comments import CommentedMap, CommentedSeq, Comment

logger = logging.getLogger(__name__)


def update_value_preserving_comments(
    commented_obj: Union[CommentedMap, dict],
    key: Union[str, int],
    new_value: Any
) -> bool:
    """
    Update a value in CommentedMap/CommentedSeq while preserving attached comments.

    Handles:
    - Inline comments: key: value  # this comment
    - End-of-line comments
    - Comment tokens attached to keys

    Args:
        commented_obj: CommentedMap or CommentedSeq object
        key: Key to update (str for maps, int for sequences)
        new_value: New value to set

    Returns:
        True if comments were preserved, False if no comments found

    Example:
        >>> from ruamel.yaml import YAML
        >>> yaml = YAML()
        >>> data = yaml.load("key: value  # important comment")
        >>> update_value_preserving_comments(data, 'key', 'new_value')
        True
        >>> # Result: "key: new_value  # important comment"
    """
    if not isinstance(commented_obj, (CommentedMap, CommentedSeq)):
        # Not a ruamel.yaml structure, fallback to direct assignment
        commented_obj[key] = new_value
        return False

    # Save comment data before modification
    ca = commented_obj.ca  # Comment attribute

    # For CommentedMap: comments are stored in ca.items[key]
    # For CommentedSeq: comments are stored in ca.items[index]
    saved_comment = None
    if hasattr(ca, 'items') and ca.items and key in ca.items:
        saved_comment = ca.items[key]
        logger.debug(f"Preserved comment for key '{key}': {saved_comment}")

    # Update the value (this may lose comment attachment)
    commented_obj[key] = new_value

    # Restore comment if it existed
    if saved_comment is not None:
        # Re-attach the comment to the updated key
        if not hasattr(ca, 'items') or ca.items is None:
            # Initialize items dict if needed
            from ruamel.yaml.comments import Comment as CommentClass
            ca.items = {}

        ca.items[key] = saved_comment
        return True

    return False


def insert_preserving_comments(
    commented_seq: Union[CommentedSeq, list],
    index: int,
    new_item: Any,
    preserve_spacing: bool = True
) -> bool:
    """
    Insert item into CommentedSeq while preserving surrounding comments.

    Handles:
    - Comments above the insertion point
    - Comments below the insertion point
    - Blank lines (formatting)
    - Comment shifting (indices change after insertion)

    Args:
        commented_seq: CommentedSeq object
        index: Index to insert at (0-based)
        new_item: Item to insert
        preserve_spacing: If True, preserve blank lines around insertion

    Returns:
        True if comments were preserved, False if no comments found

    Example:
        >>> yaml = YAML()
        >>> data = yaml.load('''
        ... items:
        ...   # Comment for item 1
        ...   - item1
        ...   - item2
        ... ''')
        >>> insert_preserving_comments(data['items'], 1, 'new_item')
        True
    """
    if not isinstance(commented_seq, CommentedSeq):
        # Not a ruamel.yaml structure, fallback to direct insertion
        commented_seq.insert(index, new_item)
        return False

    ca = commented_seq.ca

    # Step 1: Collect comments that will need to be shifted
    # When we insert at index N, all comments at indices >= N shift by +1
    comments_to_shift = {}
    if hasattr(ca, 'items') and ca.items:
        for i, comment in ca.items.items():
            if isinstance(i, int) and i >= index:
                comments_to_shift[i] = comment
                logger.debug(f"Will shift comment at index {i} to {i+1}")

    # Step 2: Insert the new item
    commented_seq.insert(index, new_item)

    # Step 3: Shift comments to new indices
    if comments_to_shift:
        # Remove old indices
        for old_index in comments_to_shift.keys():
            if old_index in ca.items:
                del ca.items[old_index]

        # Add at new indices (shifted by +1)
        for old_index, comment in comments_to_shift.items():
            new_index = old_index + 1
            ca.items[new_index] = comment

        return True

    return False


def delete_preserving_comments(
    commented_obj: Union[CommentedMap, CommentedSeq, dict, list],
    key: Union[str, int],
    preserve_orphaned_comments: bool = True
) -> Optional[Any]:
    """
    Delete item while handling orphaned comments appropriately.

    Handles:
    - Inline comments on deleted items
    - Block comments above deleted items
    - Comment shifting (for sequences)
    - Orphaned comment preservation

    Args:
        commented_obj: CommentedMap or CommentedSeq object
        key: Key to delete (str for maps, int for sequences)
        preserve_orphaned_comments: If True, attach orphaned comments to next item

    Returns:
        The deleted value, or None if key didn't exist

    Example:
        >>> yaml = YAML()
        >>> data = yaml.load('''
        ... items:
        ...   # This is item 1
        ...   item1: value1  # inline comment
        ...   item2: value2
        ... ''')
        >>> delete_preserving_comments(data['items'], 'item1', preserve_orphaned_comments=True)
        'value1'
        >>> # Result: orphaned comments moved to item2
    """
    # Check if key exists (different logic for maps vs sequences)
    if isinstance(commented_obj, (CommentedSeq, list)):
        if not isinstance(key, int) or key < 0 or key >= len(commented_obj):
            logger.warning(f"Index '{key}' out of range, cannot delete")
            return None
    else:
        if key not in commented_obj:
            logger.warning(f"Key '{key}' not found in object, cannot delete")
            return None

    # Get the value before deletion
    deleted_value = commented_obj[key]

    if not isinstance(commented_obj, (CommentedMap, CommentedSeq)):
        # Not a ruamel.yaml structure, fallback to direct deletion
        del commented_obj[key]
        return deleted_value

    ca = commented_obj.ca

    # Step 1: Check if deleted item has comments
    orphaned_comment = None
    if hasattr(ca, 'items') and ca.items and key in ca.items:
        orphaned_comment = ca.items[key]
        logger.debug(f"Found orphaned comment on deleted key '{key}': {orphaned_comment}")

    # Step 2: Delete the item
    del commented_obj[key]

    # Step 3: Handle orphaned comments
    if orphaned_comment and preserve_orphaned_comments:
        if isinstance(commented_obj, CommentedMap):
            # For maps: Try to attach to next item
            keys = list(commented_obj.keys())
            if keys:
                next_key = keys[0]
                logger.debug(f"Attaching orphaned comment to next key '{next_key}'")
                # Prepend to existing comment if any
                if hasattr(ca, 'items') and ca.items and next_key in ca.items:
                    # Merge comments (complex - for now, just replace)
                    ca.items[next_key] = orphaned_comment
                else:
                    if not hasattr(ca, 'items') or ca.items is None:
                        ca.items = {}
                    ca.items[next_key] = orphaned_comment

        elif isinstance(commented_obj, CommentedSeq):
            # For sequences: Shift comments down by -1
            # All comments at indices > deleted_index shift by -1
            if isinstance(key, int) and hasattr(ca, 'items') and ca.items:
                comments_to_shift = {}
                for i, comment in ca.items.items():
                    if isinstance(i, int) and i > key:
                        comments_to_shift[i] = comment

                # Remove old indices
                for old_index in comments_to_shift.keys():
                    if old_index in ca.items:
                        del ca.items[old_index]

                # Add at new indices (shifted by -1)
                for old_index, comment in comments_to_shift.items():
                    new_index = old_index - 1
                    ca.items[new_index] = comment

                # Attach orphaned comment to the item now at deleted index
                if len(commented_obj) > key:
                    ca.items[key] = orphaned_comment

    return deleted_value


def get_comment(
    commented_obj: Union[CommentedMap, CommentedSeq],
    key: Union[str, int]
) -> Optional[Any]:
    """
    Get the comment attached to a specific key/index.

    Args:
        commented_obj: CommentedMap or CommentedSeq object
        key: Key to get comment for

    Returns:
        Comment object if found, None otherwise

    Example:
        >>> yaml = YAML()
        >>> data = yaml.load("key: value  # my comment")
        >>> comment = get_comment(data, 'key')
        >>> comment is not None
        True
    """
    if not isinstance(commented_obj, (CommentedMap, CommentedSeq)):
        return None

    ca = commented_obj.ca
    if hasattr(ca, 'items') and ca.items and key in ca.items:
        return ca.items[key]

    return None


def set_comment(
    commented_obj: Union[CommentedMap, CommentedSeq],
    key: Union[str, int],
    comment_text: str,
    position: str = 'eol'  # 'eol' (end of line) or 'above' (block comment)
) -> bool:
    """
    Set or update a comment on a specific key/index.

    Note: This function uses ruamel.yaml's yaml_set_comment_before_after_key method
    which is the recommended way to add comments programmatically.

    Args:
        commented_obj: CommentedMap or CommentedSeq object
        key: Key to attach comment to
        comment_text: Comment text (without # prefix)
        position: 'eol' for inline, 'above' for block comment

    Returns:
        True if comment was set, False otherwise

    Example:
        >>> yaml = YAML()
        >>> data = yaml.load("key: value")
        >>> set_comment(data, 'key', 'important field', position='eol')
        True
        >>> # Result: "key: value  # important field"
    """
    if not isinstance(commented_obj, (CommentedMap, CommentedSeq)):
        return False

    try:
        # Use ruamel.yaml's built-in method for setting comments
        if isinstance(commented_obj, CommentedMap):
            if position == 'eol':
                # End-of-line comment (after the value)
                commented_obj.yaml_add_eol_comment(comment_text, key=key)
            else:
                # Block comment before the key
                commented_obj.yaml_set_comment_before_after_key(key, before=comment_text)
        elif isinstance(commented_obj, CommentedSeq):
            # For sequences, use index
            if position == 'eol':
                commented_obj.yaml_add_eol_comment(comment_text, key)
            else:
                commented_obj.yaml_set_comment_before_after_key(key, before=comment_text)

        logger.debug(f"Set {position} comment on key '{key}': {comment_text}")
        return True
    except Exception as e:
        logger.warning(f"Failed to set comment on key '{key}': {e}")
        return False


def has_comment(
    commented_obj: Union[CommentedMap, CommentedSeq],
    key: Union[str, int]
) -> bool:
    """
    Check if a key/index has an attached comment.

    Args:
        commented_obj: CommentedMap or CommentedSeq object
        key: Key to check

    Returns:
        True if comment exists, False otherwise
    """
    return get_comment(commented_obj, key) is not None


def copy_comments(
    source_obj: Union[CommentedMap, CommentedSeq],
    target_obj: Union[CommentedMap, CommentedSeq],
    keys: Optional[List[Union[str, int]]] = None
) -> int:
    """
    Copy comments from source to target object.

    Args:
        source_obj: Source CommentedMap/CommentedSeq
        target_obj: Target CommentedMap/CommentedSeq
        keys: Optional list of keys to copy (None = all keys)

    Returns:
        Number of comments copied

    Example:
        >>> yaml = YAML()
        >>> source = yaml.load("key: value  # comment")
        >>> target = yaml.load("key: new_value")
        >>> copy_comments(source, target)
        1
        >>> # Result: target now has "key: new_value  # comment"
    """
    if not isinstance(source_obj, (CommentedMap, CommentedSeq)):
        return 0
    if not isinstance(target_obj, (CommentedMap, CommentedSeq)):
        return 0

    source_ca = source_obj.ca
    target_ca = target_obj.ca

    # Ensure target has items dict
    if not hasattr(target_ca, 'items') or target_ca.items is None:
        target_ca.items = {}

    if not hasattr(source_ca, 'items') or not source_ca.items:
        return 0

    # Determine which keys to copy
    if keys is None:
        keys = list(source_ca.items.keys())

    copied_count = 0
    for key in keys:
        if key in source_ca.items and key in target_obj:
            target_ca.items[key] = source_ca.items[key]
            copied_count += 1
            logger.debug(f"Copied comment for key '{key}'")

    return copied_count


# Convenience aliases for shorter code
preserve_update = update_value_preserving_comments
preserve_insert = insert_preserving_comments
preserve_delete = delete_preserving_comments
