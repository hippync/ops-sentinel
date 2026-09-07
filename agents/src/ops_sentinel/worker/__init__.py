"""Worker — investigate with read-only tools, propose a fix.

In: Incident. Out: FixProposal, with a required rollback plan and evidence refs.

The iteration cap (risk row 3) is enforced by the graph runtime, NOT here and NOT
in the prompt. A cap the agent enforces on itself is not a cap. On breach: fail
loudly, page a human, log partial state — never continue with a partial result.
"""
