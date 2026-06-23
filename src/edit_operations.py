"""
Unified edit operations model for music retargeting.

This module provides a unified representation for both trim (remove segments)
and extend (repeat segments) operations, enabling a common optimization framework.

Research backing:
- Dynamic Programming for sequence alignment (Viterbi algorithm)
- Music retargeting as constrained optimization problem
- Common representation allows globally optimal solutions for both modes
"""

from dataclasses import dataclass
from typing import Literal, Tuple, List
from enum import Enum


class EditType(Enum):
    """Type of edit operation."""
    KEEP = "keep"      # Keep segment as-is
    REMOVE = "remove"  # Remove segment (trim mode)
    REPEAT = "repeat"  # Repeat segment (extend mode)


@dataclass(frozen=True)
class Segment:
    """
    Represents a music segment with boundaries and metadata.

    Segments are the atomic units of editing - typically aligned to
    beats, bars, or section boundaries for musical coherence.
    """
    start: float  # Start time in seconds
    end: float    # End time in seconds
    label: str = "unknown"  # Section label (verse, chorus, etc.)
    similarity: float = 0.0  # Similarity to other segments (for repetition)
    energy: float = 0.0      # Energy level (for importance)

    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end - self.start

    def __repr__(self) -> str:
        return f"Segment({self.start:.1f}-{self.end:.1f}s, {self.label})"


@dataclass(frozen=True)
class EditOperation:
    """
    Unified representation of an edit operation.

    This replaces the separate TrimStrategy cut_points and loop_points
    with a single, unified model that works for both modes.

    Examples:
        - Keep:   EditOperation(KEEP, Segment(0, 10), repeat_count=1)
        - Remove: EditOperation(REMOVE, Segment(10, 20), repeat_count=0)
        - Repeat: EditOperation(REPEAT, Segment(20, 30), repeat_count=3)
    """
    operation: EditType
    segment: Segment
    repeat_count: int = 1  # 1 for KEEP/REMOVE, >1 for REPEAT

    def __post_init__(self):
        """Validate the operation."""
        if self.operation == EditType.REMOVE and self.repeat_count != 0:
            raise ValueError("REMOVE operation must have repeat_count=0")
        if self.operation == EditType.KEEP and self.repeat_count != 1:
            raise ValueError("KEEP operation must have repeat_count=1")
        if self.operation == EditType.REPEAT and self.repeat_count < 2:
            raise ValueError("REPEAT operation must have repeat_count>=2")

    @property
    def duration_change(self) -> float:
        """Calculate the duration change this operation causes."""
        base_duration = self.segment.duration

        if self.operation == EditType.REMOVE:
            return -base_duration
        elif self.operation == EditType.REPEAT:
            return base_duration * (self.repeat_count - 1)
        else:  # KEEP
            return 0.0

    def __repr__(self) -> str:
        if self.operation == EditType.KEEP:
            return f"Keep({self.segment.start:.1f}-{self.segment.end:.1f}s)"
        elif self.operation == EditType.REMOVE:
            return f"Remove({self.segment.start:.1f}-{self.segment.end:.1f}s)"
        else:
            return f"Repeat({self.segment.start:.1f}-{self.segment.end:.1f}s, {self.repeat_count}x)"


@dataclass
class EditSequence:
    """
    A sequence of edit operations that transforms audio to target length.

    This replaces TrimStrategy and provides a unified representation
    for both trim and extend modes.
    """
    operations: List[EditOperation]
    target_length: float
    original_length: float
    mode: Literal["trim", "extend"]

    @property
    def resulting_length(self) -> float:
        """Calculate resulting length after applying all operations."""
        total_change = sum(op.duration_change for op in self.operations)
        return self.original_length + total_change

    @property
    def length_error(self) -> float:
        """Calculate absolute error from target length."""
        return abs(self.resulting_length - self.target_length)

    def to_trim_strategy(self):
        """
        Convert to legacy TrimStrategy format for backward compatibility.

        This allows the new unified system to work with existing
        output_generator and quality_scorer code.
        """
        from src.trim_engine import TrimStrategy

        # Extract cut_points (REMOVE operations)
        cut_points = []
        for op in self.operations:
            if op.operation == EditType.REMOVE:
                cut_points.append((op.segment.start, op.segment.end))

        # Extract loop_points (REPEAT operations)
        loop_points = []
        for op in self.operations:
            if op.operation == EditType.REPEAT:
                loop_points.append((
                    op.segment.start,
                    op.segment.end,
                    op.repeat_count
                ))

        # Fade regions will be computed by output_generator
        fade_regions = []

        return TrimStrategy(
            name=self.mode,
            cut_points=cut_points,
            loop_points=loop_points,
            fade_regions=fade_regions,
            target_length=self.target_length
        )

    @classmethod
    def from_trim_strategy(cls, strategy, original_length: float, mode: str):
        """
        Create EditSequence from legacy TrimStrategy for testing/migration.
        """
        operations = []

        # Convert cut_points to REMOVE operations
        for start, end in strategy.cut_points:
            seg = Segment(start, end)
            operations.append(EditOperation(EditType.REMOVE, seg, 0))

        # Convert loop_points to REPEAT operations
        for start, end, repeat_count in strategy.loop_points:
            seg = Segment(start, end)
            operations.append(EditOperation(EditType.REPEAT, seg, repeat_count))

        return cls(
            operations=operations,
            target_length=strategy.target_length,
            original_length=original_length,
            mode=mode
        )

    def __repr__(self) -> str:
        ops_str = ", ".join(str(op) for op in self.operations[:3])
        if len(self.operations) > 3:
            ops_str += f", ... ({len(self.operations)} total)"
        return f"EditSequence({self.mode}, {ops_str})"


def validate_edit_sequence(seq: EditSequence, tolerance: float = 15.0) -> bool:
    """
    Validate that an edit sequence meets basic constraints.

    Args:
        seq: The edit sequence to validate
        tolerance: Maximum allowed length error in seconds

    Returns:
        True if valid, raises ValueError if invalid
    """
    # Check length accuracy
    if seq.length_error > tolerance:
        raise ValueError(
            f"Length error {seq.length_error:.1f}s exceeds tolerance {tolerance}s"
        )

    # Check no overlapping operations
    for i, op1 in enumerate(seq.operations):
        for op2 in seq.operations[i+1:]:
            if not (op1.segment.end <= op2.segment.start or
                    op2.segment.end <= op1.segment.start):
                raise ValueError(
                    f"Overlapping operations: {op1} and {op2}"
                )

    # Check operations are in temporal order
    sorted_ops = sorted(seq.operations, key=lambda op: op.segment.start)
    if sorted_ops != seq.operations:
        raise ValueError("Operations must be in temporal order")

    return True
