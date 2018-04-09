"""
This module provides utilities for grouping objects into namespaces.
"""
from inspect import isfunction
import logging

from ophyd import Device

from .utils import (IterableNamespace, find_class, strip_prefix,
                    extract_objs)

logger = logging.getLogger(__name__)


def class_namespace(cls, scope=None):
    """
    Create a ``namespace`` that contains objects of a specific type.

    Parameters
    ----------
    cls: ``type`` or ``str``

    scope: ``module``, ``namespace``, or ``list`` of these
        Every object attached to the given modules will be considered for the
        `class_namespace`. If ``scope`` is omitted, we'll check all objects
        loaded by ``hutch-python`` and everything in the caller's global frame.
        If anything is an instance of ``ophyd.Device``, we'll also include the
        object's components as part of the scope, using the ``name`` attribute
        to identify them rather than the attribute name on the device. This
        will continue recursively.

    Returns
    -------
    namespace: `IterableNamespace`
    """
    logger.debug('Create class_namespace cls=%s, scope=%s', cls, scope)
    class_space = IterableNamespace()
    scope_objs = extract_objs(scope=scope, stack_offset=1)

    if isinstance(cls, str):
        if cls != 'function':
            try:
                cls = find_class(cls)
            except Exception as exc:
                err = 'Type {} could not be loaded'
                logger.error(err.format(cls))
                logger.debug(exc, exc_info=True)
                return class_space

    cache = set()

    # Helper function to recursively add subdevices to the scope
    def accumulate(obj, scope_objs, cache):
        if obj not in cache:
            cache.add(obj)
            for comp_name in getattr(obj, 'component_names', []):
                sub_obj = getattr(obj, comp_name)
                accumulate(sub_obj, scope_objs, cache)
            # Don't accidentally override
            if obj.name not in scope_objs:
                scope_objs[obj.name] = obj

    for name, obj in scope_objs.copy().items():
        if isinstance(obj, Device):
            accumulate(obj, scope_objs, cache)

    for name, obj in scope_objs.items():
        include = False
        if cls == 'function':
            if isfunction(obj):
                include = True
        elif isinstance(obj, cls):
            include = True
        if include:
            setattr(class_space, name, obj)
            logger.debug('Include %s in cls=%s namespace', name, cls)

    return class_space


def metadata_namespace(md, scope=None):
    """
    Create a ``namespace`` that accumulates objects and creates a tree based on
    their metadata.

    Parameters
    ----------
    md: ``list`` of ``str``
        Each of the metadata categories to group objects by, in order from the
        root of the tree to the leaves.

    scope: ``module``, ``namespace``, or ``list`` of these
        Every object attached to the given modules will be considered for the
        `metadata_namespace`. If ``scope`` is omitted, we'll check all objects
        loaded by ``hutch-python`` and everything in the caller's global frame.

    Returns
    -------
    namespace: `IterableNamespace`
    """
    logger.debug('Create metadata_namespace md=%s, scope=%s', md, scope)
    metadata_space = IterableNamespace()
    scope_objs = extract_objs(scope=scope, stack_offset=1)

    for name, obj in scope_objs.items():
        # Collect obj metadata
        if hasattr(obj, 'md'):
            raw_keys = [getattr(obj.md, filt, None) for filt in md]
        # Fallback: use_the_name
        else:
            if '_' not in name:
                continue
            name_keys = name.split('_')
            raw_keys = name_keys[:len(md)]
        # Abandon if no matches
        if raw_keys[0] is None:
            continue
        # Force lowercase
        keys = []
        for key in raw_keys:
            if isinstance(key, str):
                keys.append(key.lower())
            else:
                keys.append(key)
        # Add key to existing namespace branch, create new if needed
        logger.debug('Add %s to metadata namespace', name)
        upper_space = metadata_space
        for key in keys:
            if key is None:
                break
            name = strip_prefix(name, key)
            if not hasattr(upper_space, key):
                setattr(upper_space, key, IterableNamespace())
            upper_space = getattr(upper_space, key)
        setattr(upper_space, name, obj)
    return metadata_space