# Redux Module Pattern

This project now uses a module registry to compose reducers.

## How to add a new module slice

1. Create module slice file:
- `src/modules/<modulo>/store/<modulo>Slice.js`

2. Create module store descriptor:
- `src/modules/<modulo>/store/index.js`

Descriptor shape:

```js
export const moduloStoreModule = {
  key: 'modulo',
  reducer: moduloReducer,
}
```

3. Register module in:
- `src/store/moduleRegistry.js`

```js
import { moduloStoreModule } from '@/modules/modulo/store'

export const STORE_MODULES = [
  // ...other modules
  moduloStoreModule,
]
```

No changes are needed in `src/store/index.js` or `src/test/utils/createTestStore.js`.
Both are built from the shared module registry.
