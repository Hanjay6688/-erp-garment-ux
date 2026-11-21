# CP7.5 retained test inputs

This directory supplies the exact original ZIP bytes for three synthetic GitHub Actions artifacts. The released SKU workflow checks the ZIP and its original report as usual. The source run, byte count, and SHA-256 for each input are in `archives.json`.

The CP7.5 audit runner requests the original BF in its normal manner. Astra may include a second encrypted response bound to that job's request to open these three stored artifacts. The read helper verifies the encrypted package and every ZIP. During input preparation, the GitHub CLI adapter tries the original endpoint first. It uses the verified local copy only after an HTTP 404 or 410 for a listed ZIP. The final run artifact records the original run, GitHub status, and checksum for each use.

The ERP product under test is `48858590`. The clock and factory candidate is `47f88383`. All run data are synthetic and `production_go=false`.
