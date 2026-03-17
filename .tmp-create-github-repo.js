const { chromium } = require('playwright');

const REPO_NAME = 'shop';
const FALLBACK_NAME = 'shop-20260308';
const VISIBILITY = 'private';
const NEW_REPO_URL = 'https://github.com/new';

async function waitForLoginIfNeeded(context, page) {
  const needsLogin =
    page.url().includes('/login') ||
    await page.locator('input[name="login"]').count() > 0;

  if (!needsLogin) {
    return page;
  }

  console.log('ACTION REQUIRED: Complete GitHub sign-in in the opened browser window.');

  const deadline = Date.now() + 600000;
  while (Date.now() < deadline) {
    for (const candidate of context.pages()) {
      if (candidate.isClosed()) {
        continue;
      }

      const currentUrl = candidate.url();
      if (/github\.com\/new(\?.*)?$/.test(currentUrl)) {
        return candidate;
      }
    }

    await page.waitForTimeout(1000);
  }

  throw new Error('Timed out waiting for GitHub login to complete.');
}

async function selectVisibility(page) {
  if (VISIBILITY === 'private') {
    const privateRadio = page.locator('input#repository_visibility_private, input[value="private"]');
    if (await privateRadio.count()) {
      await privateRadio.check();
    }
  }
}

async function disableAutoInit(page) {
  const autoInit = page.locator('input#repository_auto_init');
  if (await autoInit.count()) {
    try {
      if (await autoInit.isChecked()) {
        await autoInit.uncheck();
      }
    } catch {
      // Ignore if GitHub changes the control behavior.
    }
  }
}

async function fillRepoName(page, name) {
  const repoInput = page.locator('input[name="repository[name]"], input#repository_name');
  await repoInput.waitFor({ timeout: 60000 });
  await repoInput.fill('');
  await repoInput.fill(name);
  await page.waitForTimeout(1500);
}

async function getCreateButton(page) {
  return page.getByRole('button', { name: /create repository/i });
}

async function tryCreate(page, name) {
  await fillRepoName(page, name);
  await selectVisibility(page);
  await disableAutoInit(page);

  const createButton = await getCreateButton(page);
  const disabled = await createButton.isDisabled();
  if (disabled) {
    return { success: false, reason: 'create-button-disabled' };
  }

  await createButton.click();

  try {
    await page.waitForURL(new RegExp(`github\\.com/[^/]+/${name.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}$`), {
      timeout: 20000,
    });
    return { success: true, name, url: page.url() };
  } catch {
    return { success: false, reason: 'navigation-timeout' };
  }
}

(async () => {
  const browser = await chromium.launch({
    channel: 'msedge',
    headless: false,
    slowMo: 100,
  });

  let page = await browser.newPage({ viewport: { width: 1440, height: 960 } });

  await page.goto(NEW_REPO_URL, {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });

  page = await waitForLoginIfNeeded(page.context(), page);

  if (!page.url().includes('/new')) {
    await page.goto(NEW_REPO_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
  }

  let result = await tryCreate(page, REPO_NAME);
  if (!result.success) {
    console.log(`Primary name failed: ${result.reason}`);
    await page.goto(NEW_REPO_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    });
    result = await tryCreate(page, FALLBACK_NAME);
  }

  if (!result.success) {
    throw new Error(`Failed to create repository with both names. Last reason: ${result.reason}`);
  }

  console.log(`repo_name=${result.name}`);
  console.log(`repo_url=${result.url}`);

  await page.waitForTimeout(2000);
  await browser.close();
})();
