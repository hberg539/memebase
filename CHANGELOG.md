# Changelog

## [0.4.0](https://github.com/hberg539/memebase/compare/v0.3.0...v0.4.0) (2026-02-23)


### Features

* trigger search immediately on Enter key press ([2555278](https://github.com/hberg539/memebase/commit/2555278c38e8b78f4d432d6604888888c007f743))


### Bug Fixes

* **frontend:** cross-browser compatibility for Safari and Chrome ([02dc0d4](https://github.com/hberg539/memebase/commit/02dc0d482da754c1608ff23db0b4fff465e1c582))
* keep duplicate files on disk during meme registration ([95f576c](https://github.com/hberg539/memebase/commit/95f576caf3544b67d91e51960f6dd3077499616a))
* **service:** skip rename and DB update when AI-suggested name is unchanged ([b60a31a](https://github.com/hberg539/memebase/commit/b60a31a867525087d3616c3e52fb7b09ea2b877c))
* **ui:** keyboard handling for bulk tag and auto-detect modals ([6f1567e](https://github.com/hberg539/memebase/commit/6f1567e9636956a2ed7373a8295764fbcee462c6))
* use Flask g object for per-request DB connection management ([2df5fcc](https://github.com/hberg539/memebase/commit/2df5fcc5bbafd6b6f06c85896b8410e831716f88))


### Refactoring

* **ai:** accept model and prompt as parameters in analyze_meme ([aa6fb3e](https://github.com/hberg539/memebase/commit/aa6fb3ea4d3c117f3462c6dbeb855d65f18aac5f))
* **app:** extract business logic from route handlers into service layer ([0424337](https://github.com/hberg539/memebase/commit/04243371883a461056b2167b5ac7ffc494e5586d))
* **app:** move late imports to module level ([3ac2034](https://github.com/hberg539/memebase/commit/3ac203479cfcbfc19a19dc25a307a60d3c69ed1b))
* centralize config loading into dedicated config module ([8428e77](https://github.com/hberg539/memebase/commit/8428e77887192e579a48efb2cecc179deca1a428))
* **db:** decompose query_memes into helper functions ([9e84087](https://github.com/hberg539/memebase/commit/9e840873bac7c3510d3349e087ebede6e532b5d4))
* **db:** move normalize_tags from db.py to util.py ([5fc3499](https://github.com/hberg539/memebase/commit/5fc34993c73948af2b87089d3c8ac7a09bd58a06))
* migrate from os.path to pathlib.Path for all filesystem operations ([5f33712](https://github.com/hberg539/memebase/commit/5f3371206eba73d9a17edeb3fb114c123190c64e))
* turn src/ into proper memebase package ([338a546](https://github.com/hberg539/memebase/commit/338a546fcac4aeb884098baf62d44e8840107fb4))
* **types:** add AppConfig TypedDict for structured config access ([6d37462](https://github.com/hberg539/memebase/commit/6d37462fe1d05f60dddad6627dec040f6cb36a8c))
* **types:** add Meme TypedDict for structured meme records ([3767155](https://github.com/hberg539/memebase/commit/3767155001f55ca64ca8e0192106d07e18fb0007))
* **types:** replace magic error strings with MemeError StrEnum ([ce1a5a0](https://github.com/hberg539/memebase/commit/ce1a5a0c897a1bb70756f41a3688355e773e3779))


### Performance

* cache config in memory after first load ([7f7d588](https://github.com/hberg539/memebase/commit/7f7d588da80d2c7c3ee387c0ce4569d8c714afde))
* **db:** add indexes, fix N+1 query, and batch tag operations ([2108d72](https://github.com/hberg539/memebase/commit/2108d72b6696f0ad5a904f7701f2f0cf3cf85091))
* **db:** use RETURNING clause in increment_copy_count and delete_meme_row ([2ddd781](https://github.com/hberg539/memebase/commit/2ddd78140f249df9904d18250df28fca838f13aa))


### Styling

* extract CACHE_MAX_AGE constant, consolidate TOML parsing, simplify normalize_tags ([c12d84e](https://github.com/hberg539/memebase/commit/c12d84e7ce8ac2b461e6e2b3f487bdca5718e6cf))


### Tests

* **api:** add HTTP-level endpoint tests with mocked service/DB ([7f4a20f](https://github.com/hberg539/memebase/commit/7f4a20ff8d35647e47b5304b1095014a6cb4d7a5))
* **api:** add URL scheme validation tests for meme download endpoint ([15deb23](https://github.com/hberg539/memebase/commit/15deb23f95f781cdb29b05ec00dee3903a011bc6))
* **config:** add deep-merge tests for old/partial/empty configs ([49762f5](https://github.com/hberg539/memebase/commit/49762f575f03f072de19298f66502f20d3964177))


### Build System

* **config:** bump minimum Python version to 3.11 ([ebae0b7](https://github.com/hberg539/memebase/commit/ebae0b79a38e4f47ccb914384365b775ae70dbc2))
* disable debug mode in Docker image ([f52f9e7](https://github.com/hberg539/memebase/commit/f52f9e7d4b294a0b40665d1315e7d85a9adeb046))


### Miscellaneous

* ignore .claude/ directory ([85ad159](https://github.com/hberg539/memebase/commit/85ad1594be65b2b745f892988846bdf127e9551f))
* **lint:** enable stricter ruff rules and fix all violations ([21df54b](https://github.com/hberg539/memebase/commit/21df54b5ae9db4a2338fb9feb432cec9ed35db3e))

## [0.3.0](https://github.com/hberg539/memebase/compare/v0.2.0...v0.3.0) (2026-02-23)


### Features

* **ui:** add rainbow gradient favicon with build script ([949b34b](https://github.com/hberg539/memebase/commit/949b34b547c68785372c60ad712fbf8cffc57411))


### Bug Fixes

* **config:** use local build instead of remote image in docker-compose ([28ca6e9](https://github.com/hberg539/memebase/commit/28ca6e9a9a5bbff46342540c2b726ff285e8dc59))
* **grid:** truncate long meme filenames with ellipsis while preserving extension ([bd268f0](https://github.com/hberg539/memebase/commit/bd268f0e8afb97767137e4cce40ac1e14c323359))
* **security:** validate URL scheme in upload-from-url endpoint ([299987c](https://github.com/hberg539/memebase/commit/299987c9d1ecd7caac44c2d2f0bbd348dbe53b5e))


### Refactoring

* extract service layer, split ai.py, deduplicate upload logic ([b4f1720](https://github.com/hberg539/memebase/commit/b4f17200899e7727258091689f62c2f890f1419f))


### Documentation

* add links to README badges ([5d42b0c](https://github.com/hberg539/memebase/commit/5d42b0ca116ff2f7734bac4e3aec29b423077dcb))
* add test status badge to README ([67f8a07](https://github.com/hberg539/memebase/commit/67f8a07100512fc693f6ab35622d0eee0473ab7a))
* update AGENTS.md with service layer, new tests, and CI info ([51ceaa6](https://github.com/hberg539/memebase/commit/51ceaa6d75c2d9b629dc31ed5f470a86e8f6d440))


### Styling

* add type hints to all Python source functions ([cade51a](https://github.com/hberg539/memebase/commit/cade51ac2feb6b057095ca48f514645e761909c1))


### Build System

* sync uv.lock version via release-please extra-files ([08685f6](https://github.com/hberg539/memebase/commit/08685f6593a7704887becc9fc0130d85afd4ecbb))


### CI/CD

* add pytest workflow for every push and PR ([5b6b6c0](https://github.com/hberg539/memebase/commit/5b6b6c0918cf271f56d8a4a666c15bed92b75b33))
* test on Python 3.10 and 3.14 ([2e69b9a](https://github.com/hberg539/memebase/commit/2e69b9af207bfeb937dc01d32d04b86b8c8ce538))


### Miscellaneous

* remove TODOS.md ([c3ac1ec](https://github.com/hberg539/memebase/commit/c3ac1ece3543f0910f0dd57c58f7fdb9a068ecd0))

## [0.2.0](https://github.com/hberg539/memebase/compare/v0.1.0...v0.2.0) (2026-02-23)


### Features

* initial memebase implementation ([e086855](https://github.com/hberg539/memebase/commit/e0868552346dbd21f1b7da95e0c709ba75568dfe))
