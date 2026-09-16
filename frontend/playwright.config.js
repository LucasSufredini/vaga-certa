import { defineConfig } from '@playwright/test';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const db=join(mkdtempSync(join(tmpdir(),'vaga-e2e-')), 'browser.db');
export default defineConfig({
  testDir:'./tests', workers:1, timeout:30000,
  use:{baseURL:'http://127.0.0.1:8001',headless:true,
    launchOptions:process.env.CHROMIUM_EXECUTABLE?{executablePath:process.env.CHROMIUM_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage']}:{}},
  webServer:{command:`${process.env.PYTHON_EXECUTABLE||'python'} -m uvicorn app.main:app --host 127.0.0.1 --port 8001`,
    cwd:'../backend',url:'http://127.0.0.1:8001/api/health',reuseExistingServer:false,
    env:{DATABASE_URL:`sqlite:///${db}`,OPERATOR_TOKEN:'demo-local',DEMO_MODE:'true'},timeout:30000}
});
