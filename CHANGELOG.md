# Changelog

## [0.2.0](https://github.com/stritti/nak-district-planner/compare/nak-district-planner-v0.1.0...nak-district-planner-v0.2.0) (2026-04-16)


### Features

* Add 'Entschlafenen-Gottesdienst' as a computed feast, enhance its display in the MatrixView, and update the use case documentation. ([d85947b](https://github.com/stritti/nak-district-planner/commit/d85947bc0257f4c97f951315fd71b74c871edce3))
* add approval-based IDP onboarding and pending alerts ([06b84c3](https://github.com/stritti/nak-district-planner/commit/06b84c3e691bfd7e32f36e12276ae9adb7c1e58f))
* Add automated Keycloak realm setup scripts (phase4a tasks 1.4–1.8) ([4cd1f75](https://github.com/stritti/nak-district-planner/commit/4cd1f757c1440dfb200d95f33fe179eb45fd360d))
* add CalDAV, Google, and Microsoft calendar connectors with unit tests ([7f81d28](https://github.com/stritti/nak-district-planner/commit/7f81d289ea3243f5e7b796f43af4ae9c0f0bf0ab))
* add draft generation and matrix move workflow ([e45f958](https://github.com/stritti/nak-district-planner/commit/e45f9586cf6f0dc1c23ef284fa7329e9117f2737))
* Add event filtering by group to the event list view and backend API. ([995b34f](https://github.com/stritti/nak-district-planner/commit/995b34fe713ab815edfff462c672b654571554d9))
* add event-based invitation workflow in service matrix ([6875958](https://github.com/stritti/nak-district-planner/commit/6875958f3c9e3f9f5512717c939536f3798bdc14))
* Add GitHub Actions workflows for CI, security, dependency, and code quality checks ([#1](https://github.com/stritti/nak-district-planner/issues/1)) ([2e390bf](https://github.com/stritti/nak-district-planner/commit/2e390bf7565c3bb9e4d6c91b75a7732f586cc591))
* add OIDC debug logging and implement logout listener in auth store ([5dcf88d](https://github.com/stritti/nak-district-planner/commit/5dcf88d6cb07984f910e05a6fef96563800a6fdf))
* add openspec configuration for auto-generating 8-week draft services ([a0565a6](https://github.com/stritti/nak-district-planner/commit/a0565a6761a250feb59a9318af6b1f2e7292dea7))
* add OpenSpec for approved IDP onboarding ([ffe095a](https://github.com/stritti/nak-district-planner/commit/ffe095afe8ae9236c1898e8bf5f9d88cf53e53a8))
* Add OpenTelemetry distributed tracing to the backend ([#33](https://github.com/stritti/nak-district-planner/issues/33)) ([65ddbdb](https://github.com/stritti/nak-district-planner/commit/65ddbdb827caa00f4eed9d6dff645928de243697))
* add pluggable IDP provisioning layer ([63d5e66](https://github.com/stritti/nak-district-planner/commit/63d5e66f12bf13a9b06e1a05075a2d62544f8e76))
* Add service times to congregations with corresponding backend, database, and frontend updates. ([6f275bf](https://github.com/stritti/nak-district-planner/commit/6f275bfba71e29873b0f51b6534196d4e14c93ad))
* add state variables for self-linking leaders in LeadersAdminView ([e33f6b6](https://github.com/stritti/nak-district-planner/commit/e33f6b6e2c09b176fbe8af3eae7f103a3757f649))
* Autocomplete name input for service leader matrix with gap highlighting ([#20](https://github.com/stritti/nak-district-planner/issues/20)) ([5273447](https://github.com/stritti/nak-district-planner/commit/5273447d426f91cb64dcb3cb1c4b2ff753b5fcca))
* Automated SemVer release pipeline via release-please ([#34](https://github.com/stritti/nak-district-planner/issues/34)) ([958d9e5](https://github.com/stritti/nak-district-planner/commit/958d9e542502974a186d73ff92d8bdd4d1cd8864))
* Create Keycloak-Deploy stack (phase4a tasks 1.1–1.3) ([326a01f](https://github.com/stritti/nak-district-planner/commit/326a01f43ef4b40aa2d190b1d0b4e5cc974725c0))
* Create phase4a-jwt-auth-minimal (minimal JWT auth for MVP deployment) ([86a9c5e](https://github.com/stritti/nak-district-planner/commit/86a9c5ef40fe4ed1fc0b70d620d40c8ace48d4c9))
* enhance OIDC authentication with multi-strategy token validation and configurable logging ([441acb8](https://github.com/stritti/nak-district-planner/commit/441acb88aa5c59cc77a9296d5c977d0f7298012b))
* Excel export for Dienstplan-Matrix and Ereignis-Übersicht ([#17](https://github.com/stritti/nak-district-planner/issues/17)) ([f1e45d9](https://github.com/stritti/nak-district-planner/commit/f1e45d9260ce9287490d59408bd7c989f13bc216))
* Feiertage hervorheben ([d221b59](https://github.com/stritti/nak-district-planner/commit/d221b590e3c13f9f56271824abb9bd457e9406f4))
* Frontend unit tests (Vitest) + complete CI pipeline ([#7](https://github.com/stritti/nak-district-planner/issues/7)) ([8ec72d0](https://github.com/stritti/nak-district-planner/commit/8ec72d0afb3111abf6899d58b20f4466044e7483))
* group congregations and sync district selection ([ef51686](https://github.com/stritti/nak-district-planner/commit/ef5168658ef9ab6bbc3570b6dc492ce01c19223b))
* IDP-agnostic self-registration workflow for Amtsträger ([#36](https://github.com/stritti/nak-district-planner/issues/36)) ([e512a66](https://github.com/stritti/nak-district-planner/commit/e512a661b8c791a8d5c17c22d6ffe9402df8a12e))
* Implement event auto-categorization for 'Gottesdienst' and add filtering for district-level events in the UI and API. ([6a80176](https://github.com/stritti/nak-district-planner/commit/6a8017619194ca5251479f09412fe2f7e54e3b89))
* Implement full CRUD for leaders with dedicated backend API, database models, and frontend administration view. ([0568d23](https://github.com/stritti/nak-district-planner/commit/0568d23479ddbc35f7ebf3d631d514205e354461))
* Implement holiday import functionality, add `state_code` to districts, and `default_category` to calendar integrations. ([610b788](https://github.com/stritti/nak-district-planner/commit/610b7889eb06d0073c320f6395a78dbef4d6bb5f))
* Implement initial full-stack application structure for district planning, service assignments, and calendar integration. ([abd942e](https://github.com/stritti/nak-district-planner/commit/abd942e0fcfcb1f0ddd84ce3d80bfb52a8ba5eda))
* Implement rank and special role-based sorting for leaders within sections, removing the immediate alphabetical sort on new leader creation. ([784223c](https://github.com/stritti/nak-district-planner/commit/784223cbe829d3bfad9aece1bca99b59f90113e8))
* implement user-leader linking, superadmin role, and initial test data seeding ([b81124a](https://github.com/stritti/nak-district-planner/commit/b81124a75da9d2dccb40416cf1d8fbb6182694bb))
* introduce `CryptoError` for decryption failures and update error handling in calendar integration and sync services. ([722f490](https://github.com/stritti/nak-district-planner/commit/722f49053ddde082d19a200c8e016a5ff371f081))
* introduce congregation groups to organize congregations within districts. ([98cd13d](https://github.com/stritti/nak-district-planner/commit/98cd13d28b7d062bb6cc76823ac02ea36df4fdac))
* Introduce OpenSpec framework with multiple change proposals and integrate with various AI agents for change management. ([096d0b0](https://github.com/stritti/nak-district-planner/commit/096d0b005fd6a86eec18f862eb0ccf0d19508e09))
* introduce VitePress documentation site ([335633d](https://github.com/stritti/nak-district-planner/commit/335633d18158a913837ed12b8c3f9fd529ef0a3f))
* monthly Celery job to purge events older than 24 months ([#19](https://github.com/stritti/nak-district-planner/issues/19)) ([89b6045](https://github.com/stritti/nak-district-planner/commit/89b60450f531789e2ca5a2326ced2efd74b4d3d7))
* optimize matrix view for wider, denser planning ([0c0ca94](https://github.com/stritti/nak-district-planner/commit/0c0ca949f75fe38754d404ba18b36787db33a68f))
* upgrade frontend to Tailwind CSS v4 with light/dark mode theme and CSS component classes ([#21](https://github.com/stritti/nak-district-planner/issues/21)) ([606f766](https://github.com/stritti/nak-district-planner/commit/606f76641ecf2823562b91b22ff722c43da2a185))


### Bug Fixes

* allow replacing and clearing matrix assignments ([9ff2072](https://github.com/stritti/nak-district-planner/commit/9ff20723b57c15ca5c8ab32e3cf99444f6601f31))
* Assignemnt of feiertage ([9f1316c](https://github.com/stritti/nak-district-planner/commit/9f1316c2ef3118be8c4669cd9275821f0e7fb0d2))
* **ci:** add skip-release-pulls parameter directly to workflow ([330e9e7](https://github.com/stritti/nak-district-planner/commit/330e9e7a370b5f09a166a9fef201a1a60e78399d))
* **ci:** change release workflow trigger from push to workflow_dispatch ([d24686b](https://github.com/stritti/nak-district-planner/commit/d24686b169de2fb334adfa9bb3a70cba3a5e537b))
* **ci:** enable automatic releases on push to main ([e07d439](https://github.com/stritti/nak-district-planner/commit/e07d4399ef357239791e99614f10469c6ec96b53))
* ignore vitepres cache ([cd83fd6](https://github.com/stritti/nak-district-planner/commit/cd83fd6c0e6b56382afb47e88689a3d63cab72af))
* Keycloak 26.5.6 compatibility - use '--optimized' flag and explicit build ([a88d45b](https://github.com/stritti/nak-district-planner/commit/a88d45bd6a0105b90086665419169d9b7749d0de))
* **release:** use PAT token for release-please and opt into Node.js 24 ([#61](https://github.com/stritti/nak-district-planner/issues/61)) ([29ceb22](https://github.com/stritti/nak-district-planner/commit/29ceb2206f98bdf19202a69827d184028ac03246))
* remove ignore ([074ebdb](https://github.com/stritti/nak-district-planner/commit/074ebdb921e54256d3e071ac98b110cc664044d0))
* repair broken VitePress docs build ([#37](https://github.com/stritti/nak-district-planner/issues/37)) ([d4e9367](https://github.com/stritti/nak-district-planner/commit/d4e93671a5987982061ce6eb2fc75fb9dfac6627))
* resolve two CI failures — OIDC validators block test collection and VitePress missing dependency ([#39](https://github.com/stritti/nak-district-planner/issues/39)) ([0cf40f2](https://github.com/stritti/nak-district-planner/commit/0cf40f2129dedb069bc82e88d22d831f0a51e5bb))
* synchronize active district selection across admin views ([8a46758](https://github.com/stritti/nak-district-planner/commit/8a467584e40a1e8a83c330e4138f8a319174a956))
* **tests:** clear mock call history between tests in events.test.ts ([#32](https://github.com/stritti/nak-district-planner/issues/32)) ([78d9576](https://github.com/stritti/nak-district-planner/commit/78d9576225c93a39f71ac0903b90579ed742e129))


### Documentation

* Add Keycloak authentication documentation and integrate it into the navigation and sidebar. ([9adf915](https://github.com/stritti/nak-district-planner/commit/9adf91594391aca12e388b5bcc3f52e1f478e219))
* add OpenSpec artifacts for invitation matrix workflow ([1239d76](https://github.com/stritti/nak-district-planner/commit/1239d76eeef596d65be6b43f06806c033dfb793f))
* add technical plan for planning model refactor and update implementation roadmap ([f9522a8](https://github.com/stritti/nak-district-planner/commit/f9522a856e87855dd5f171c949d48c41bf6d2f7e))
* Analyse & Verbesserungsvorschläge gegen OpenSpec ([#58](https://github.com/stritti/nak-district-planner/issues/58)) ([23b5474](https://github.com/stritti/nak-district-planner/commit/23b5474b53258aab366bbff44922de1c6519fcaa))
* consolidate documentation baseline and remove phase 4b snapshots ([#73](https://github.com/stritti/nak-district-planner/issues/73)) ([d7b6302](https://github.com/stritti/nak-district-planner/commit/d7b63025dcd757d2685d7ed8507c464ad3739e97))
* define 8-week draft service pre-generation change ([f967d8c](https://github.com/stritti/nak-district-planner/commit/f967d8cdc17af7efbcb91f114df746c0b538f374))
* finalize defaults in approved IDP onboarding design ([74cbd41](https://github.com/stritti/nak-district-planner/commit/74cbd41582671d956cb4885b3b87a1d224850940))
* finalize roles.md and auth-keycloak.md, fix VitePress config ([1f468e8](https://github.com/stritti/nak-district-planner/commit/1f468e8f6fb0cbc64ac54751ab6b67ed687f2266))
* propose congregation grouping and creation dialog flow ([a0c6164](https://github.com/stritti/nak-district-planner/commit/a0c6164a392f975304478196794e4d2673a56537))
* propose role-based contextual help change ([e857431](https://github.com/stritti/nak-district-planner/commit/e8574317c02283405cc406983a5f73a9ed1baf72))
* resolve Frage 6 (everyone can create export tokens) and add keycloak comparison section ([eb14961](https://github.com/stritti/nak-district-planner/commit/eb149619aab2ad212504ac90e73b8adfad45bbc3))
* Rollen-Speicherung Empfehlung in Abschnitt 4.3 ausgebaut ([135406c](https://github.com/stritti/nak-district-planner/commit/135406c05043c61df1ae2741d3b138d30696e447))
* Rollenkonzept – DB-Modell, JWT-Widerspruch und Export-Token-Matrix korrigiert ([d1860b6](https://github.com/stritti/nak-district-planner/commit/d1860b6de5b2ee8a924f1592c64baf485f6cfded))
* Rollenkonzept – Review-Feedback eingearbeitet (Entscheidungen, Keycloak, Audit-Log) ([9cc9928](https://github.com/stritti/nak-district-planner/commit/9cc9928f990287141db961c8c75e0cebdc1a51fb))
* Rollenkonzept für NAK Bezirksplaner (finaler Stand) ([#18](https://github.com/stritti/nak-district-planner/issues/18)) ([5f1d6f9](https://github.com/stritti/nak-district-planner/commit/5f1d6f9b64823230382d0b2f94a2b2f1cc59b061))
* Rollenkonzept für NAK Bezirksplaner entworfen ([f936f8a](https://github.com/stritti/nak-district-planner/commit/f936f8ae5bbd2491788d606206472b81bf981f08))


### Code Refactoring

* improve query parameter handling in listEvents and ignore temporary backend environment files ([e3540c3](https://github.com/stritti/nak-district-planner/commit/e3540c35401d310b33660f4fd70cd09c9ea5529b))
* integrate OIDC state management into Pinia store and improve PKCE security implementation ([eb91ce4](https://github.com/stritti/nak-district-planner/commit/eb91ce4d43b372302046f2f41cb009af852296c5))
* Remove the "only district level" filter option and its associated logic from the matrix view and API. ([3491b3f](https://github.com/stritti/nak-district-planner/commit/3491b3f1ac1f2f8fce1bb4a7d6bd0b1da48f972f))
