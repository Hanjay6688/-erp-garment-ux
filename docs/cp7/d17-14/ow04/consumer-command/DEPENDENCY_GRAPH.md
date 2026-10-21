# Consumer dependency reader: isolated implementation work

This reader is implemented and locally checked, but the complete APPLY/UNDO
command is not implemented. The current full owning installer does not load
consumer/01_dependency_graph.sql. Its explicit composition barrier is retained.
No public facade, financial journal, permission grant, Native case or feature
completion follows from these controls.

The actual database reader follows note revisions and application links in both
directions, terminating cycles with UNION. It retains original and negative undo
events and historical target headers. Every connected document resolves through
the existing exact current_leaf_assignment. Cross-customer edges and a cohort
whose source belongs to another root refuse. The result includes the complete
connected headers, revision/family/cohort/consumption facts and their exact PG
JSON hash. It has no locks, live actor capability, source authority claim or
financial calculation. A future owning command must lock this complete graph
before period SHARE, then compare fresh captures and current permissions.

Ten local synthetic PGlite checks exercise cyclic/bidirectional membership,
start-node-independent fact captures, signed history, fully undone edges,
corrected target leaves, isolation, customer/root corruption, absent invoices
and outsider EXEC denial. The same retained source assignment/hash functions
are loaded unchanged. These are graph controls, not Native business commands.

Run the source driver with PGlite installed, or set OW04_PGLITE_MODULE to its
module path. The driver never connects to a server or installs the product.
The existing nine literal money expectations remain separate and unchanged.
The owning journal/poster, dated target reconciliation, request protocol,
current permissions, materialization and deferred closure still need the
complete implementation and actual Native proof before this file is loaded.
