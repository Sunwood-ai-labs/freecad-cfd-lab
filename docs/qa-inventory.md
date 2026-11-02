# Publication QA inventory

Requested outcome: publish the FreeCAD / OSS CFD experiments from the original
2026-10-29–2026-11-02 investigation as a public GitHub repository.

| Requirement / artifact | Acceptance evidence |
| --- | --- |
| Correct experiments | Compare original chat with saved outputs: Elbow, window comparison, family-house design, family-house airflow |
| Original data preserved | Copy into a new repository; never modify the original experiment workspace |
| Usable public entry points | English/Japanese README, experiment guide, environment guide, reproduction guide, limitations |
| Models, inputs, code, images | Packaging manifest, file-size audit, Python/PowerShell syntax and JSON checks |
| Large final fields available | Separate release archives, archive CRC check, SHA256 manifest and download check |
| Honest numerical claims | Inspect final saved JSON and actual final velocity-field hash; distinguish 585 from final 697 |
| Licensing and public payload | Third-party notices, source provenance, secret/path review; exclude local preferences and auth |
| GitHub publication | Public visibility, default branch contents, exact pushed commit and release asset list |
| Automated repository checks | Validation workflow succeeds on the published commit |

Publishing checks validate the packaged repository and historical evidence.
They do not constitute a fresh CFD solve, a fresh container build, or a complete
replay of the adapted scripts on another computer. See [reproduction](reproduction.md).

Concrete check results are recorded in [publication-validation.json](publication-validation.json)
and the publication release notes.
