## Changelog
All notable changes to this project will be documented in this file. <br/>
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.2.3-Beta
- Added guided installation command support via `etracker install`
- Fixed CLI dispatch so install mode no longer falls through to tracking/report output
- Improved install UX by handling `Ctrl+C` gracefully without traceback

## 0.2.2-Beta 
- Added a new feature to display old transaction history by CLI
  e.g. `etracker --month 10 --year 2023`
- Added `--interval` option to get the transaction data for a specific interval and unit seconds
  e.g. `etracker --interval 10` # Every 10 seconds