# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Jayakrishna Ichapurapu
# module-id: 12d07a5e-169bc35c
"""Resolution Layer - Neo 3.0 Conflict Prevention Engine"""

from .expertise_resolver import ExpertiseResolver
from .intent_merger import IntentMerger
from .agent_negotiator import AgentNegotiator

__all__ = [
    'ExpertiseResolver',
    'IntentMerger',
    'AgentNegotiator'
]
