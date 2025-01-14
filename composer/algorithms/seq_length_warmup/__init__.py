# Copyright 2021 MosaicML. All Rights Reserved.

"""Sequence length warmup progressively increases the sequence length during training of NLP models.

See the :doc:`Method Card </method_cards/seq_length_warmup>` for more details.
"""

from composer.algorithms.seq_length_warmup.seq_length_warmup import SeqLengthWarmup, set_batch_sequence_length

__all__ = ["SeqLengthWarmup", "set_batch_sequence_length"]
