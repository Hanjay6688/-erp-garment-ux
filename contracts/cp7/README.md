# CP7 transport contracts

Runtime decoders for the authored RPC shapes. They are typechecked by the root
build and exercised by `tests/cp7`. Until a consumer is connected, these modules
are not shipped in the browser application. A connected consumer must import
and actually use the decoder; the existing source/RPC ownership gate remains
unchanged. No side-effect-only import or orphan exception is permitted.

This directory is not a planning engine. Authoritative quantity, allocation,
matching, timeline and financial computations belong to the modular PostgreSQL
engine required by framework ADR-01. Client contracts validate transport only.
