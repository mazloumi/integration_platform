/* JSONMapper - Complete Implementation
 * Visual JSON mapping with backend integration
*/

class JSONMapper {
  constructor(options = {}) {
    this.container = typeof options.container === 'string' 
      ? document.querySelector(options.container)
      : options.container || document.body;
    
    this.onSave = options.onSave || (() => {});
    this.apiBaseUrl = options.apiBaseUrl || '/api';
    this.integrationId = options.integrationId || null;
    
    this.sourceData = null;
    this.targetSchema = null;
    this.mappings = [];
    this.integrations = [];
    this.currentIntegration = null;
    this.webhookEndpoints = new Map();
    
    this.transformations = {
      'none': { label: 'No transformation', fn: (v) => v },
      'uppercase': { label: 'Uppercase', fn: (v) => String(v).toUpperCase() },
      'lowercase': { label: 'Lowercase', fn: (v) => String(v).toLowerCase() },
      'trim': { label: 'Trim whitespace', fn: (v) => String(v).trim() },
      'number': { label: 'To number', fn: (v) => Number(v) },
      'string': { label: 'To string', fn: (v) => String(v) },
      'boolean': { label: 'To boolean', fn: (v) => Boolean(v) },
      'date': { label: 'To date string', fn: (v) => new Date(v).toISOString() },
      'concat': { label: 'Concatenate', fn: (v, param) => String(v) + String(param || '') },
      'replace': { label: 'Replace text', fn: (v, search, replace) => String(v).replace(search || '', replace || '') },
      'split': { label: 'Split by delimiter', fn: (v, delim) => String(v).split(delim || ',') },
      'join': { label: 'Join array', fn: (v, delim) => Array.isArray(v) ? v.join(delim || ',') : v },
      'javascript': { label: 'Custom JavaScript', fn: null, isCustom: true }
    };
    
    this.init();
  }

  init() {
    this.render();
    this.attachEventListeners();
    this.checkUrlParameters();
  }

  render() {
    this.container.innerHTML = `
      <div class="json-mapper">
        <div class="json-mapper-section">
          <h2>📥 Step 1: Configure Integration</h2>
          
          <div class="json-mapper-form-group">
            <label>Integration Name</label>
            <input type="text" class="json-mapper-input" id="integration-name" placeholder="My Integration">
          </div>

          <h3>Source Configuration</h3>
          <div class="json-mapper-form-group">
            <label>Source Type</label>
            <select class="json-mapper-select" id="source-type">
              <option value="webhook">Webhook</option>
              <option value="pubsub">Google Cloud Pub/Sub</option>
            </select>
          </div>

          <div id="webhook-config">
            <div class="json-mapper-info">
              <strong>📡 Webhook Endpoint</strong>
              <div class="json-mapper-copy-box">
                <input type="text" class="json-mapper-copy-input" id="webhook-url" readonly value="">
                <button class="json-mapper-btn json-mapper-btn-primary json-mapper-btn-small" id="copy-webhook">Copy URL</button>
                <button class="json-mapper-btn json-mapper-btn-success json-mapper-btn-small" id="generate-webhook">Generate</button>
              </div>
              <p style="margin: 10px 0 0 0; font-size: 12px;">Share this URL to receive webhook events</p>
            </div>
          </div>

          <div id="pubsub-config" style="display: none;">
            <div class="json-mapper-grid">
              <div class="json-mapper-form-group">
                <label>GCP Project ID</label>
                <input type="text" class="json-mapper-input" id="pubsub-project" placeholder="my-project-id">
              </div>
              <div class="json-mapper-form-group">
                <label>Topic Name</label>
                <input type="text" class="json-mapper-input" id="pubsub-topic" placeholder="my-topic">
              </div>
            </div>
            <div class="json-mapper-grid">
              <div class="json-mapper-form-group">
                <label>Subscription Name</label>
                <input type="text" class="json-mapper-input" id="pubsub-subscription" placeholder="my-subscription">
              </div>
              <div class="json-mapper-form-group">
                <label>Subscription Mode</label>
                <select class="json-mapper-select" id="pubsub-subscription-mode">
                  <option value="push">Push (Google sends to endpoint)</option>
                  <option value="pull">Pull (We check periodically)</option>
                </select>
              </div>
            </div>
            <div class="json-mapper-grid">
              <div class="json-mapper-form-group" id="pull-interval-group" style="display: none;">
                <label>Pull Interval (seconds)</label>
                <input type="number" class="json-mapper-input" id="pubsub-pull-interval" placeholder="60" value="60" min="10">
              </div>
              <div class="json-mapper-form-group">
                <label>Service Account JSON (paste content)</label>
                <textarea class="json-mapper-textarea" id="pubsub-credentials" placeholder='{"type": "service_account", ...}' style="height: 100px;"></textarea>
              </div>
            </div>
            <div class="json-mapper-info" style="margin-top: 10px;" id="push-mode-info">
              <small>💡 The push endpoint will be automatically generated when you save the integration.</small>
            </div>
            <div class="json-mapper-info" style="margin-top: 10px; display: none;" id="pull-mode-info">
              <small>💡 Pull mode will check for new messages at the specified interval in the background.</small>
            </div>
          </div>

          <h3>Target Configuration</h3>
          <div class="json-mapper-grid">
            <div class="json-mapper-form-group">
              <label>Target Type</label>
              <select class="json-mapper-select" id="integration-target-type">
                <option value="http">HTTP/HTTPS</option>
                <option value="email">Email (SMTP)</option>
              </select>
            </div>
          </div>

          <div id="http-target-config">
          <div class="json-mapper-grid">
            <div class="json-mapper-form-group">
              <label>HTTP Method</label>
              <select class="json-mapper-select" id="integration-method">
                <option value="GET">GET</option>
                <option value="POST">POST</option>
              </select>
            </div>
            <div class="json-mapper-form-group">
              <label>Authentication</label>
              <select class="json-mapper-select" id="integration-auth">
                <option value="none">None</option>
                <option value="bearer">Bearer Token</option>
                <option value="basic">Basic Auth</option>
                <option value="apikey">API Key</option>
              </select>
            </div>
          </div>
          <div class="json-mapper-form-group">
            <label>Target URL</label>
            <input type="text" class="json-mapper-input" id="integration-url" placeholder="https://api.example.com/endpoint">
          </div>

          <div id="integration-auth-config" style="display: none;">
            <div class="json-mapper-form-group" id="integration-bearer-config" style="display: none;">
              <label>Bearer Token</label>
              <input type="text" class="json-mapper-input" id="integration-bearer-token" placeholder="your-token-here">
            </div>
            <div id="integration-basic-config" style="display: none;">
              <div class="json-mapper-grid">
                <div class="json-mapper-form-group">
                  <label>Username</label>
                  <input type="text" class="json-mapper-input" id="integration-basic-username" placeholder="username">
                </div>
                <div class="json-mapper-form-group">
                  <label>Password</label>
                  <input type="password" class="json-mapper-input" id="integration-basic-password" placeholder="password">
                </div>
              </div>
            </div>
            <div id="integration-apikey-config" style="display: none;">
              <div class="json-mapper-grid">
                <div class="json-mapper-form-group">
                  <label>Header Name</label>
                  <input type="text" class="json-mapper-input" id="integration-apikey-header" placeholder="X-API-Key">
                </div>
                <div class="json-mapper-form-group">
                  <label>API Key</label>
                  <input type="text" class="json-mapper-input" id="integration-apikey-value" placeholder="your-api-key">
                </div>
              </div>
            </div>
          </div>

          <div class="json-mapper-form-group">
            <label>Custom Headers (one per line)</label>
            <textarea class="json-mapper-textarea" id="integration-headers" style="height: 80px;" placeholder="Content-Type: application/json"></textarea>
          </div>
          </div>

          <div id="email-target-config" style="display: none;">
            <div class="json-mapper-info">
              <strong>📧 Email Configuration</strong>
              <p style="margin: 10px 0 0 0; font-size: 12px;">Transformed data will be sent as email body</p>
            </div>
            <div class="json-mapper-grid">
              <div class="json-mapper-form-group">
                <label>SMTP Server</label>
                <input type="text" class="json-mapper-input" id="email-smtp-server" placeholder="smtp.gmail.com">
              </div>
              <div class="json-mapper-form-group">
                <label>SMTP Port</label>
                <input type="number" class="json-mapper-input" id="email-smtp-port" placeholder="587" value="587">
              </div>
            </div>
            <div class="json-mapper-grid">
              <div class="json-mapper-form-group">
                <label>SMTP Username</label>
                <input type="text" class="json-mapper-input" id="email-smtp-username" placeholder="your-email@example.com">
              </div>
              <div class="json-mapper-form-group">
                <label>SMTP Password</label>
                <input type="password" class="json-mapper-input" id="email-smtp-password" placeholder="your-password">
              </div>
            </div>
            <div class="json-mapper-grid">
              <div class="json-mapper-form-group">
                <label>From Email</label>
                <input type="email" class="json-mapper-input" id="email-from" placeholder="sender@example.com">
              </div>
              <div class="json-mapper-form-group">
                <label>To Email(s) (comma-separated)</label>
                <input type="text" class="json-mapper-input" id="email-to" placeholder="recipient@example.com">
              </div>
            </div>
            <div class="json-mapper-form-group">
              <label>Email Subject</label>
              <input type="text" class="json-mapper-input" id="email-subject" placeholder="Integration Notification">
            </div>
            <div class="json-mapper-form-group">
              <label>Use TLS/SSL</label>
              <select class="json-mapper-select" id="email-use-tls">
                <option value="true">Yes (TLS)</option>
                <option value="false">No</option>
              </select>
            </div>
          </div>

          <h3>Execution Condition (Optional)</h3>
          <div class="json-mapper-form-group">
            <label>Condition JavaScript (leave empty to always execute)</label>
            <textarea class="json-mapper-textarea" id="integration-condition" style="height: 100px;" placeholder="// Return true to execute, false to skip&#10;// Access source fields using: fields['field.path']&#10;// Example: return fields['event'] === 'user.created'"></textarea>
            <button class="json-mapper-btn json-mapper-btn-primary json-mapper-btn-small" id="test-condition" style="margin-top: 5px;">Test Condition</button>
            <div id="condition-test-result" style="display: none; margin-top: 10px;"></div>
            <div class="json-mapper-info" style="margin-top: 10px;">
              <small>💡 The condition evaluates source data. Only if it returns <code>true</code>, the transformation and API call will execute. All incoming events are logged as integration runs.</small>
            </div>
          </div>

          <button class="json-mapper-btn json-mapper-btn-success" id="save-integration">Validate Integration</button>

          <div id="saved-integrations" style="margin-top: 20px; display: none;">
            <h3>Integration</h3>
            <div id="integrations-list"></div>
          </div>
        </div>

        <div class="json-mapper-section" id="integration-mapping-section" style="display: none;">
          <h2>🗺️ Step 2: Configure Field Mapping</h2>
          <div class="json-mapper-grid">
            <div class="json-mapper-form-group">
              <label>Source JSON (Sample Event)</label>
              <textarea class="json-mapper-textarea" id="integration-source-json" placeholder='{"event": "user.created", "data": {...}}'></textarea>
              <button class="json-mapper-btn json-mapper-btn-primary json-mapper-btn-small" id="integration-load-source">Load Source</button>
              <div id="integration-source-error" class="json-mapper-error" style="display:none;"></div>
            </div>
            <div class="json-mapper-form-group">
              <label id="integration-target-schema-label">Target JSON Schema</label>
              <textarea class="json-mapper-textarea" id="integration-target-json" placeholder='{"name": "", "email": ""}'></textarea>
              <button class="json-mapper-btn json-mapper-btn-primary json-mapper-btn-small" id="integration-load-target">Load Target</button>
              <div id="integration-target-error" class="json-mapper-error" style="display:none;"></div>
            </div>
          </div>

          <div id="integration-mapping-fields" style="display: none; margin-top: 20px;">
            <h3>Field Mappings</h3>
            <div class="json-mapper-grid">
              <div>
                <h4>Source Fields</h4>
                <div class="json-mapper-field-list" id="integration-source-fields"></div>
              </div>
              <div>
                <h4 id="integration-target-fields-label">Target Fields</h4>
                <div class="json-mapper-field-list" id="integration-target-fields"></div>
              </div>
            </div>
            
            <div class="json-mapper-mappings" id="integration-mappings-container">
              <p style="color: #999;">No mappings yet</p>
            </div>

            <button class="json-mapper-btn json-mapper-btn-success json-mapper-btn-small" id="integration-add-mapping">+ Add Mapping</button>
          </div>
        </div>

        <div class="json-mapper-section" id="integration-test-section" style="display: none;">
          <h2>🧪 Step 3: Test Integration</h2>
          <div class="json-mapper-tabs">
            <button class="json-mapper-tab active" data-tab="integration-preview">Preview Output</button>
            <button class="json-mapper-tab" data-tab="integration-runs">Integration Runs</button>
          </div>

          <div class="json-mapper-tab-content active" id="tab-integration-preview">
            <button class="json-mapper-btn json-mapper-btn-primary" id="integration-test-mapping">Preview Mapping</button>
            <div class="json-mapper-output" id="integration-output-preview">Output will appear here</div>
          </div>

          <div class="json-mapper-tab-content" id="tab-integration-runs">
            <button class="json-mapper-btn json-mapper-btn-primary" id="view-runs">📊 Load Integration Runs</button>
            <div class="json-mapper-output" id="integration-runs-output">Click button to load integration runs</div>
          </div>
        </div>
        <div class="json-mapper-section" id="integration-save-section" style="display: none;">
          <h2>🗺️ Step 4: Save & Execute</h2>
          <div id="validation-message" class="json-mapper-info" style="display: none; margin-bottom: 15px;"></div>
          <button class="json-mapper-btn json-mapper-btn-primary" id="save-to-backend" style="display: none;">💾 Save to Backend</button>
          <div id="execute-section" style="margin-top: 20px; display: none;">
            <h3>Execute Integration</h3>
            <p class="json-mapper-info">Send the sample source JSON to the webhook endpoint to test the full integration pipeline.</p>
            <button class="json-mapper-btn json-mapper-btn-warning" id="integration-test-api">🚀 Execute Full Integration</button>
            <div class="json-mapper-output" id="integration-api-response" style="margin-top: 10px;">Save integration first, then execute to see results</div>
          </div>
        </div>
      </div>
    `;
  }

  attachEventListeners() {
    // Source configuration
    document.getElementById('source-type').addEventListener('change', (e) => { this.updateSourceConfig(e.target.value); this.markAsChanged(); });
    document.getElementById('generate-webhook').addEventListener('click', () => { this.generateWebhook(); this.markAsChanged(); });
    document.getElementById('copy-webhook').addEventListener('click', () => this.copyWebhookUrl());
    document.getElementById('pubsub-subscription-mode').addEventListener('change', (e) => { this.updatePubSubModeUI(e.target.value); this.markAsChanged(); });

    // Target configuration
    document.getElementById('integration-target-type').addEventListener('change', (e) => { this.updateTargetTypeConfig(e.target.value); this.markAsChanged(); });
    document.getElementById('integration-auth').addEventListener('change', (e) => { this.updateIntegrationAuthConfig(e.target.value); this.markAsChanged(); });
    document.getElementById('integration-method').addEventListener('change', (e) => { this.updateIntegrationMethodUI(e.target.value); this.markAsChanged(); });

    // Track changes on all input fields
    this.container.querySelectorAll('input, select, textarea').forEach(element => {
      if (!['copy-webhook', 'copy-curl'].includes(element.id)) {
        element.addEventListener('change', () => this.markAsChanged());
        element.addEventListener('input', () => this.markAsChanged());
      }
    });

    // Integration management
    document.getElementById('save-integration').addEventListener('click', () => this.saveIntegration());
    document.getElementById('save-to-backend').addEventListener('click', () => this.saveIntegrationToBackend());
    //document.getElementById('load-from-backend').addEventListener('click', () => this.showLoadIntegrationDialog());
    document.getElementById('test-condition').addEventListener('click', () => this.testCondition());
    
    // Mapping configuration
    document.getElementById('integration-load-source').addEventListener('click', () => this.loadIntegrationSource());
    document.getElementById('integration-load-target').addEventListener('click', () => this.loadIntegrationTarget());
    document.getElementById('integration-add-mapping').addEventListener('click', () => this.addMapping());
    
    // Testing
    document.getElementById('integration-test-mapping').addEventListener('click', () => this.testIntegrationMapping());
    document.getElementById('integration-test-api').addEventListener('click', () => this.executeIntegrationApi());
    document.getElementById('view-runs').addEventListener('click', () => this.showIntegrationRunsDialog());

    // Tabs
    this.container.querySelectorAll('.json-mapper-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        const tabName = e.target.dataset.tab;
        const parent = e.target.closest('.json-mapper-section');
        parent.querySelectorAll('.json-mapper-tab').forEach(t => t.classList.remove('active'));
        parent.querySelectorAll('.json-mapper-tab-content').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        parent.querySelector('#tab-' + tabName).classList.add('active');
      });
    });
  }

  checkUrlParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    const integrationId = urlParams.get('integration_id');

    if (integrationId) {
      this.loadIntegrationFromBackend(integrationId);
    }
  }

  markAsChanged() {
    if (this.isChanged) return; // Already marked as changed

    this.isChanged = true;

    // Hide Save to Backend button
    const saveBtn = document.getElementById('save-to-backend');
    if (saveBtn) {
      saveBtn.style.display = 'none';
    }

    // Update validation message
    const validationMsg = document.getElementById('validation-message');
    if (validationMsg) {
      validationMsg.textContent = '⚠️ Integration has been modified. Please validate again before saving to backend.';
      validationMsg.style.display = 'block';
      validationMsg.style.color = '#d97706';
    }
  }

  // === SOURCE CONFIGURATION ===

  updateSourceConfig(sourceType) {
    document.getElementById('webhook-config').style.display = sourceType === 'webhook' ? 'block' : 'none';
    document.getElementById('pubsub-config').style.display = sourceType === 'pubsub' ? 'block' : 'none';
  }

  updatePubSubModeUI(mode) {
    const pullIntervalGroup = document.getElementById('pull-interval-group');
    const pushModeInfo = document.getElementById('push-mode-info');
    const pullModeInfo = document.getElementById('pull-mode-info');

    if (mode === 'pull') {
      pullIntervalGroup.style.display = 'block';
      pushModeInfo.style.display = 'none';
      pullModeInfo.style.display = 'block';
    } else {
      pullIntervalGroup.style.display = 'none';
      pushModeInfo.style.display = 'block';
      pullModeInfo.style.display = 'none';
    }
  }

  updateTargetTypeConfig(targetType) {
    document.getElementById('http-target-config').style.display = targetType === 'http' ? 'block' : 'none';
    document.getElementById('email-target-config').style.display = targetType === 'email' ? 'block' : 'none';
  }

  generateWebhook() {
    const webhookId = 'wh_' + Math.random().toString(36).substr(2, 16);
    // This is a temporary preview URL - the actual URL will be generated by the backend
    // using SITE_URL from settings when the integration is saved
    const webhookUrl = window.location.origin + '/webhook/' + webhookId + "/";
    document.getElementById('webhook-url').value = webhookUrl;
    this.webhookEndpoints.set(webhookId, { id: webhookId, url: webhookUrl, events: [] });
  }

  copyWebhookUrl() {
    const input = document.getElementById('webhook-url');
    input.select();
    navigator.clipboard.writeText(input.value).then(() => {
      const btn = document.getElementById('copy-webhook');
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => btn.textContent = originalText, 2000);
    });
  }

  // === TARGET CONFIGURATION ===

  updateIntegrationAuthConfig(authType) {
    document.getElementById('integration-auth-config').style.display = authType === 'none' ? 'none' : 'block';
    document.getElementById('integration-bearer-config').style.display = authType === 'bearer' ? 'block' : 'none';
    document.getElementById('integration-basic-config').style.display = authType === 'basic' ? 'block' : 'none';
    document.getElementById('integration-apikey-config').style.display = authType === 'apikey' ? 'block' : 'none';
  }

  updateIntegrationMethodUI(method) {
    const targetSchemaLabel = document.getElementById('integration-target-schema-label');
    const targetFieldsLabel = document.getElementById('integration-target-fields-label');
    
    if (method === 'GET') {
      targetSchemaLabel.textContent = 'URL Parameters (as JSON keys)';
      targetFieldsLabel.textContent = 'URL Parameters';
    } else {
      targetSchemaLabel.textContent = 'Target JSON Schema (POST Body)';
      targetFieldsLabel.textContent = 'Target Fields';
    }
  }

  // === INTEGRATION MANAGEMENT ===

  saveIntegration() {
    const name = document.getElementById('integration-name').value.trim();
    const sourceType = document.getElementById('source-type').value;
    const targetType = document.getElementById('integration-target-type').value;
    const method = document.getElementById('integration-method').value;
    const url = document.getElementById('integration-url').value.trim();
    const authType = document.getElementById('integration-auth').value;
    const condition = document.getElementById('integration-condition').value.trim();

    if (!name) {
      alert('Please provide integration name');
      return;
    }

    if (targetType === 'http' && !url) {
      alert('Please provide target URL');
      return;
    }

    // Limit to one integration - clear existing integrations
    this.integrations = [];

    const integration = {
      id: Date.now(),
      name: name,
      sourceType: sourceType,
      sourceConfig: {},
      target: {
        type: targetType,
        method: method,
        url: url,
        authType: authType,
        auth: {},
        headers: {}
      },
      mappings: this.mappings || [],
      condition: condition || null
    };

    if (sourceType === 'webhook') {
      let webhookUrl = document.getElementById('webhook-url').value;
      // Ensure trailing slash
      if (webhookUrl && !webhookUrl.endsWith('/')) {
        webhookUrl += '/';
        document.getElementById('webhook-url').value = webhookUrl;
      }
      integration.sourceConfig.webhookUrl = webhookUrl;
    } else if (sourceType === 'pubsub') {
      integration.sourceConfig.projectId = document.getElementById('pubsub-project').value;
      integration.sourceConfig.topicId = document.getElementById('pubsub-topic').value;
      integration.sourceConfig.subscription = document.getElementById('pubsub-subscription').value;
      integration.sourceConfig.subscriptionMode = document.getElementById('pubsub-subscription-mode').value;
      integration.sourceConfig.pullIntervalSeconds = parseInt(document.getElementById('pubsub-pull-interval').value) || 60;
      integration.sourceConfig.credentials = document.getElementById('pubsub-credentials').value;
    }

    if (targetType === 'email') {
      integration.target.emailConfig = {
        smtpServer: document.getElementById('email-smtp-server').value,
        smtpPort: parseInt(document.getElementById('email-smtp-port').value) || 587,
        smtpUsername: document.getElementById('email-smtp-username').value,
        smtpPassword: document.getElementById('email-smtp-password').value,
        fromEmail: document.getElementById('email-from').value,
        toEmail: document.getElementById('email-to').value,
        subject: document.getElementById('email-subject').value,
        useTLS: document.getElementById('email-use-tls').value === 'true'
      };
    }

    if (authType === 'bearer') {
      integration.target.auth.token = document.getElementById('integration-bearer-token').value;
    } else if (authType === 'basic') {
      integration.target.auth.username = document.getElementById('integration-basic-username').value;
      integration.target.auth.password = document.getElementById('integration-basic-password').value;
    } else if (authType === 'apikey') {
      integration.target.auth.headerName = document.getElementById('integration-apikey-header').value;
      integration.target.auth.apiKey = document.getElementById('integration-apikey-value').value;
    }

    const customHeaders = document.getElementById('integration-headers').value.trim();
    if (customHeaders) {
      customHeaders.split('\n').forEach(line => {
        const parts = line.split(':');
        if (parts.length >= 2) {
          const key = parts[0].trim();
          const value = parts.slice(1).join(':').trim();
          integration.target.headers[key] = value;
        }
      });
    }

    this.integrations.push(integration);
    this.renderIntegrations();
    this.selectIntegration(integration.id);

    // Show validation success message and Save to Backend button
    const validationMsg = document.getElementById('validation-message');
    validationMsg.textContent = '✅ Integration validated successfully! You can now save to backend.';
    validationMsg.style.display = 'block';
    validationMsg.style.color = '#28a745';

    document.getElementById('save-to-backend').style.display = 'inline-block';

    // Mark as not changed after validation
    this.isChanged = false;

    alert('Integration "' + name + '" validated successfully!');
  }

  renderIntegrations() {
    const container = document.getElementById('integrations-list');
    const section = document.getElementById('saved-integrations');

    if (this.integrations.length === 0) {
      section.style.display = 'none';
      return;
    }

    section.style.display = 'block';
    const self = this;
    container.innerHTML = this.integrations.map(integration => {
      const isActive = self.currentIntegration && self.currentIntegration.id === integration.id;
      return '<div class="json-mapper-item ' + (isActive ? 'active' : '') + '" data-id="' + integration.id + '">' +
        '<div class="json-mapper-item-header">' +
          '<div>' +
            '<strong>' + integration.name + '</strong>' +
            '<span class="json-mapper-badge json-mapper-badge-' + integration.sourceType + '">' + integration.sourceType.toUpperCase() + '</span>' +
            '<span class="json-mapper-badge json-mapper-badge-' + integration.target.method.toLowerCase() + '">' + integration.target.method + '</span>' +
          '</div>' +
        '</div>' +
        '<div style="font-size: 12px; color: #666; margin-top: 5px;">' + integration.target.url + '</div>' +
        '<div style="font-size: 11px; color: #999; margin-top: 3px;">Auth: ' + integration.target.authType + ' | Mappings: ' + integration.mappings.length + ' | Condition: ' + (integration.condition ? 'Yes' : 'No') + '</div>' +
      '</div>';
    }).join('');

    container.querySelectorAll('.json-mapper-item').forEach(item => {
      item.addEventListener('click', e => {
        self.selectIntegration(parseInt(item.dataset.id));
      });
    });
  }

  selectIntegration(integrationId) {
    this.currentIntegration = this.integrations.find(i => i.id === integrationId);
    this.renderIntegrations();
    document.getElementById('integration-mapping-section').style.display = 'block';
    document.getElementById('integration-test-section').style.display = 'block';
    document.getElementById('integration-save-section').style.display = 'block';
    
    this.updateIntegrationMethodUI(this.currentIntegration.target.method);
    
    this.mappings = this.currentIntegration.mappings.slice();
    if (this.sourceData && this.targetSchema) {
      this.renderIntegrationMappings();
    }
  }

  deleteIntegration(integrationId) {
    if (!confirm('Are you sure you want to delete this integration?')) return;
    
    this.integrations = this.integrations.filter(i => i.id !== integrationId);
    if (this.currentIntegration && this.currentIntegration.id === integrationId) {
      this.currentIntegration = null;
      document.getElementById('integration-mapping-section').style.display = 'none';
      document.getElementById('integration-test-section').style.display = 'none';
      document.getElementById('integration-save-section').style.display = 'none';
    }
    this.renderIntegrations();
  }

  // === BACKEND INTEGRATION ===

  serializeIntegration() {
    if (!this.currentIntegration) {
      throw new Error('No active integration to serialize');
    }

    return {
      name: this.currentIntegration.name,
      sourceType: this.currentIntegration.sourceType,
      sourceConfig: this.currentIntegration.sourceConfig,
      target: this.currentIntegration.target,
      mappings: this.mappings.map(m => ({
        source: m.source,
        target: m.target,
        transform: m.transform,
        params: m.params,
        jsCode: m.jsCode,
        sourceFields: m.sourceFields
      })),
      sampleSource: this.sourceData,
      sampleTarget: this.targetSchema,
      condition: this.currentIntegration.condition || null
    };
  }

  async saveIntegrationToBackend() {
    if (!this.currentIntegration) {
      alert('Please configure an integration first');
      return;
    }

    try {
      const integrationData = this.serializeIntegration();
      
      const payload = {
        name: integrationData.name,
        config_json: integrationData
      };

      let response;
      if (this.integrationId) {

        console.log('Saving update');
        console.log(JSON.stringify(payload));

        response = await fetch(this.apiBaseUrl + '/integrations/' + this.integrationId + '/', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken()
          },
          body: JSON.stringify(payload)
        });
      } else {

        console.log('Saving new');
        console.log(JSON.stringify(payload));

        response = await fetch(this.apiBaseUrl + '/integrations/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken()
          },
          body: JSON.stringify(payload)
        });
      }

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save integration');
      }

      const savedIntegration = await response.json();
      this.integrationId = savedIntegration.id;

      if (savedIntegration.webhook_url) {
        let webhookUrl = savedIntegration.webhook_url;
        // Ensure trailing slash
        if (!webhookUrl.endsWith('/')) {
          webhookUrl += '/';
        }
        document.getElementById('webhook-url').value = webhookUrl;
        this.webhookUrl = webhookUrl;
      }

      // Show execute section
      document.getElementById('execute-section').style.display = 'block';

      alert('Integration saved to backend!\n\nIntegration ID: ' + savedIntegration.id);
      return savedIntegration;

    } catch (error) {
      alert('Error saving integration: ' + error.message);
      console.error('Save error:', error);
      throw error;
    }
  }

  async loadIntegrationFromBackend(integrationId) {
    try {
      const response = await fetch(this.apiBaseUrl + '/integrations/' + integrationId);

      if (!response.ok) {
        throw new Error('Failed to load integration');
      }

      const data = await response.json();
      const config = data.config_json;

      document.getElementById('integration-name').value = config.name;
      document.getElementById('source-type').value = config.sourceType;
      this.updateSourceConfig(config.sourceType);

      if (config.sourceType === 'webhook') {
        let webhookUrl = data.webhook_url || '';
        // Ensure trailing slash
        if (webhookUrl && !webhookUrl.endsWith('/')) {
          webhookUrl += '/';
        }
        document.getElementById('webhook-url').value = webhookUrl;
        this.webhookUrl = webhookUrl;
        // Show execute section since integration is already saved
        document.getElementById('execute-section').style.display = 'block';
      } else if (config.sourceType === 'pubsub') {
        document.getElementById('pubsub-project').value = config.sourceConfig.projectId || '';
        document.getElementById('pubsub-topic').value = config.sourceConfig.topicId || '';
        document.getElementById('pubsub-subscription').value = config.sourceConfig.subscription || '';
        const subscriptionMode = config.sourceConfig.subscriptionMode || 'push';
        document.getElementById('pubsub-subscription-mode').value = subscriptionMode;
        document.getElementById('pubsub-pull-interval').value = config.sourceConfig.pullIntervalSeconds || 60;
        document.getElementById('pubsub-credentials').value = config.sourceConfig.credentials || '';
        this.updatePubSubModeUI(subscriptionMode);
        // Show execute section since integration is already saved
        document.getElementById('execute-section').style.display = 'block';
      }

      const targetType = config.target.type || 'http';
      document.getElementById('integration-target-type').value = targetType;
      this.updateTargetTypeConfig(targetType);

      if (targetType === 'http') {
        document.getElementById('integration-method').value = config.target.method;
        document.getElementById('integration-url').value = config.target.url;
        document.getElementById('integration-auth').value = config.target.authType;
        this.updateIntegrationAuthConfig(config.target.authType);
      } else if (targetType === 'email') {
        const emailConfig = config.target.emailConfig || {};
        document.getElementById('email-smtp-server').value = emailConfig.smtpServer || '';
        document.getElementById('email-smtp-port').value = emailConfig.smtpPort || 587;
        document.getElementById('email-smtp-username').value = emailConfig.smtpUsername || '';
        document.getElementById('email-smtp-password').value = emailConfig.smtpPassword || '';
        document.getElementById('email-from').value = emailConfig.fromEmail || '';
        document.getElementById('email-to').value = emailConfig.toEmail || '';
        document.getElementById('email-subject').value = emailConfig.subject || '';
        document.getElementById('email-use-tls').value = emailConfig.useTLS ? 'true' : 'false';
      }

      // Load HTTP config even if not used (for compatibility)
      document.getElementById('integration-method').value = config.target.method || 'POST';
      document.getElementById('integration-url').value = config.target.url || '';
      document.getElementById('integration-auth').value = config.target.authType || 'none';
      this.updateIntegrationAuthConfig(config.target.authType || 'none');

      if (config.target.authType === 'bearer') {
        document.getElementById('integration-bearer-token').value = config.target.auth.token || '';
      } else if (config.target.authType === 'basic') {
        document.getElementById('integration-basic-username').value = config.target.auth.username || '';
        document.getElementById('integration-basic-password').value = config.target.auth.password || '';
      } else if (config.target.authType === 'apikey') {
        document.getElementById('integration-apikey-header').value = config.target.auth.headerName || '';
        document.getElementById('integration-apikey-value').value = config.target.auth.apiKey || '';
      }

      const headersText = Object.entries(config.target.headers || {})
        .map(([k, v]) => k + ': ' + v)
        .join('\n');
      document.getElementById('integration-headers').value = headersText;

      // Load condition
      document.getElementById('integration-condition').value = config.condition || '';

      this.currentIntegration = {
        id: data.id,
        name: config.name,
        sourceType: config.sourceType,
        sourceConfig: config.sourceConfig,
        target: config.target,
        mappings: config.mappings || [],
        condition: config.condition || null
      };

      this.integrationId = data.id;
      this.mappings = config.mappings || [];

      // Load sample source and target JSONs
      if (config.sampleSource) {
        this.sourceData = config.sampleSource;
        document.getElementById('integration-source-json').value = JSON.stringify(config.sampleSource, null, 2);
        this.renderIntegrationSourceFields();
      }

      if (config.sampleTarget) {
        this.targetSchema = config.sampleTarget;
        document.getElementById('integration-target-json').value = JSON.stringify(config.sampleTarget, null, 2);
        this.renderIntegrationTargetFields();
      }

      if (config.sampleSource && config.sampleTarget) {
        this.checkIntegrationReady();
      }

      if (this.mappings.length > 0 && this.sourceData && this.targetSchema) {
        this.renderIntegrationMappings();
      }

      document.getElementById('integration-mapping-section').style.display = 'block';
      document.getElementById('integration-test-section').style.display = 'block';

      alert('Integration loaded successfully!');
      return data;

    } catch (error) {
      alert('Error loading integration: ' + error.message);
      console.error('Load error:', error);
      throw error;
    }
  }

  async listIntegrations() {
    try {
      const response = await fetch(this.apiBaseUrl + '/integrations/');
      
      if (!response.ok) {
        throw new Error('Failed to fetch integrations');
      }

      return await response.json();

    } catch (error) {
      console.error('Error fetching integrations:', error);
      throw error;
    }
  }

  async getIntegrationRuns(integrationId, limit) {
    limit = limit || 10;
    try {
      const url = integrationId 
        ? this.apiBaseUrl + '/runs/?integration_id=' + integrationId + '&limit=' + limit
        : this.apiBaseUrl + '/runs/?limit=' + limit;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch integration runs');
      }

      const data = await response.json();
      return data.results || data;

    } catch (error) {
      console.error('Error fetching runs:', error);
      throw error;
    }
  }

  getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const parts = cookie.trim().split('=');
      if (parts[0] === 'csrftoken') {
        return parts[1];
      }
    }
    return '';
  }

  async showLoadIntegrationDialog() {
    try {
      const integrations = await this.listIntegrations();
      const items = integrations.results || integrations;
      
      if (items.length === 0) {
        alert('No integrations found in backend');
        return;
      }

      const integrationList = items.map(i => 
        i.id + ': ' + i.name + ' (' + i.source_type + ' → ' + i.target_method + ')'
      ).join('\n');

      const selected = prompt('Available Integrations:\n\n' + integrationList + '\n\nEnter Integration ID to load:');
      
      if (selected) {
        await this.loadIntegrationFromBackend(selected);
      }

    } catch (error) {
      alert('Error loading integrations: ' + error.message);
    }
  }

  async showIntegrationRunsDialog() {
    const integrationId = this.integrationId || (this.currentIntegration && this.currentIntegration.id);
    
    if (!integrationId) {
      alert('No integration selected. Please load or create an integration first.');
      return;
    }

    try {
      const runs = await this.getIntegrationRuns(integrationId, 20);
      
      if (runs.length === 0) {
        document.getElementById('integration-runs-output').textContent = 'No runs found for this integration';
        return;
      }

      const output = runs.map((run, idx) => {
        const time = new Date(run.created_at).toLocaleString();
        return (idx + 1) + '. ' + time + ' - ' + run.status.toUpperCase() + 
               ' (Transform: ' + (run.transformation_time_ms || 0) + 'ms, API: ' + (run.api_call_time_ms || 0) + 'ms)';
      }).join('\n');

      document.getElementById('integration-runs-output').textContent = output;

    } catch (error) {
      document.getElementById('integration-runs-output').textContent = 'Error fetching runs: ' + error.message;
    }
  }

  // === CONDITION TESTING ===

  testCondition() {
    const conditionCode = document.getElementById('integration-condition').value.trim();
    const resultDiv = document.getElementById('condition-test-result');

    if (!conditionCode) {
      resultDiv.style.display = 'block';
      resultDiv.className = 'json-mapper-info';
      resultDiv.innerHTML = '⚠️ No condition specified. Integration will always execute.';
      return;
    }

    if (!this.sourceData) {
      resultDiv.style.display = 'block';
      resultDiv.className = 'json-mapper-error';
      resultDiv.innerHTML = '❌ Please load source JSON first to test the condition.';
      return;
    }

    try {
      // Build fields object
      const fields = {};
      this.flattenObject(this.sourceData).forEach(field => {
        fields[field.path] = field.value;
      });

      // Evaluate condition
      const func = new Function('fields', conditionCode);
      const result = func(fields);

      // Display result
      resultDiv.style.display = 'block';
      if (result) {
        resultDiv.className = 'json-mapper-success';
        resultDiv.innerHTML = '✅ Condition evaluates to <strong>true</strong> - Integration will execute';
      } else {
        resultDiv.className = 'json-mapper-error';
        resultDiv.innerHTML = '❌ Condition evaluates to <strong>false</strong> - Integration will be skipped';
      }
    } catch (e) {
      resultDiv.style.display = 'block';
      resultDiv.className = 'json-mapper-error';
      resultDiv.innerHTML = '❌ Error in condition: ' + e.message;
    }
  }

  // === FIELD MAPPING ===

  loadIntegrationSource() {
    const textarea = document.getElementById('integration-source-json');
    const errorDiv = document.getElementById('integration-source-error');
    
    try {
      this.sourceData = JSON.parse(textarea.value);
      errorDiv.style.display = 'none';
      this.renderIntegrationSourceFields();
      this.checkIntegrationReady();
    } catch (e) {
      errorDiv.textContent = 'Invalid JSON: ' + e.message;
      errorDiv.style.display = 'block';
    }
  }

  loadIntegrationTarget() {
    const textarea = document.getElementById('integration-target-json');
    const errorDiv = document.getElementById('integration-target-error');
    
    try {
      this.targetSchema = JSON.parse(textarea.value);
      errorDiv.style.display = 'none';
      this.renderIntegrationTargetFields();
      this.checkIntegrationReady();
    } catch (e) {
      errorDiv.textContent = 'Invalid JSON: ' + e.message;
      errorDiv.style.display = 'block';
    }
  }

  checkIntegrationReady() {
    if (this.sourceData && this.targetSchema) {
      document.getElementById('integration-mapping-fields').style.display = 'block';
    }
  }

  flattenObject(obj, prefix) {
    prefix = prefix || '';
    const flattened = [];
    
    for (const key in obj) {
      const fullPath = prefix ? prefix + '.' + key : key;
      const value = obj[key];
      
      if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
        flattened.push.apply(flattened, this.flattenObject(value, fullPath));
      } else {
        flattened.push({
          path: fullPath,
          value: value,
          type: Array.isArray(value) ? 'array' : typeof value
        });
      }
    }
    
    return flattened;
  }

  renderIntegrationSourceFields() {
    const container = document.getElementById('integration-source-fields');
    const fields = this.flattenObject(this.sourceData);
    
    container.innerHTML = fields.map((field, idx) => {
      const valueStr = field.type === 'array' ? '' : ': ' + JSON.stringify(field.value).substring(0, 30);
      return '<div class="json-mapper-field-item" data-path="' + field.path + '" data-idx="' + idx + '">' +
        '<strong>' + field.path + '</strong>' +
        '<div style="font-size: 11px; color: #666;">' + field.type + valueStr + '</div>' +
      '</div>';
    }).join('');
  }

  renderIntegrationTargetFields() {
    const container = document.getElementById('integration-target-fields');
    const fields = this.flattenObject(this.targetSchema);
    
    container.innerHTML = fields.map((field, idx) => {
      return '<div class="json-mapper-field-item" data-path="' + field.path + '" data-idx="' + idx + '">' +
        '<strong>' + field.path + '</strong>' +
        '<div style="font-size: 11px; color: #666;">' + field.type + '</div>' +
      '</div>';
    }).join('');
  }

  addMapping(sourcePath, targetPath, transform, params, jsCode, sourceFields) {
    sourcePath = sourcePath || '';
    targetPath = targetPath || '';
    transform = transform || 'none';
    params = params || [];
    jsCode = jsCode || '';
    sourceFields = sourceFields || [];
    
    const mappingId = Date.now() + Math.random();
    this.mappings.push({
      id: mappingId,
      source: sourcePath,
      target: targetPath,
      transform: transform,
      params: params,
      jsCode: jsCode,
      sourceFields: sourceFields
    });

    this.markAsChanged();
    this.renderIntegrationMappings();
  }

  renderIntegrationMappings() {
    const container = document.getElementById('integration-mappings-container');
    
    if (this.mappings.length === 0) {
      container.innerHTML = '<p style="color: #999;">No mappings yet. Click "Add Mapping" to create one.</p>';
      return;
    }

    const sourceFields = this.sourceData ? this.flattenObject(this.sourceData) : [];
    const targetFields = this.targetSchema ? this.flattenObject(this.targetSchema) : [];
    const self = this;

    container.innerHTML = this.mappings.map(mapping => {
      const isJsTransform = mapping.transform === 'javascript';
      const needsParams = !isJsTransform && ['concat', 'replace', 'split', 'join'].indexOf(mapping.transform) !== -1;
      
      let sourceHtml = '';
      if (isJsTransform) {
        sourceHtml = '<div style="font-size: 12px; color: #666; margin-bottom: 5px;">Source Fields:</div>' +
          '<div class="json-mapper-source-fields">' +
          sourceFields.map(f => {
            const isSelected = mapping.sourceFields.indexOf(f.path) !== -1;
            return '<div class="json-mapper-source-field-chip ' + (isSelected ? 'selected' : '') + '" data-field="' + f.path + '">' +
              f.path +
            '</div>';
          }).join('') +
          '</div>';
      } else {
        sourceHtml = '<select class="json-mapper-mapping-field mapping-source">' +
          '<option value="">Select source field...</option>' +
          sourceFields.map(f => {
            return '<option value="' + f.path + '" ' + (f.path === mapping.source ? 'selected' : '') + '>' + f.path + '</option>';
          }).join('') +
          '</select>';
      }

      const targetHtml = '<select class="json-mapper-mapping-field mapping-target">' +
        '<option value="">Select target...</option>' +
        targetFields.map(f => {
          return '<option value="' + f.path + '" ' + (f.path === mapping.target ? 'selected' : '') + '>' + f.path + '</option>';
        }).join('') +
        '</select>';

      let transformHtml = '<select class="mapping-transform">' +
        Object.keys(self.transformations).map(key => {
          return '<option value="' + key + '" ' + (key === mapping.transform ? 'selected' : '') + '>' + self.transformations[key].label + '</option>';
        }).join('') +
        '</select>';

      if (needsParams) {
        transformHtml += '<input type="text" class="mapping-params" placeholder="Parameters (comma-separated)" value="' + mapping.params.join(',') + '" />';
      }

      if (isJsTransform) {
        transformHtml += '<textarea class="mapping-js-code" placeholder="// JavaScript code\nreturn fields[\'field.name\'];">' + (mapping.jsCode || '') + '</textarea>' +
          '<div style="font-size: 11px; color: #666;">Access: fields[\'field.path\']</div>';
      }

      return '<div class="json-mapper-mapping-row" data-id="' + mapping.id + '">' +
        '<div>' + sourceHtml + '</div>' +
        '<div class="json-mapper-arrow">→</div>' +
        '<div>' + targetHtml + '</div>' +
        '<div class="json-mapper-transform">' + transformHtml + '</div>' +
        '<button class="json-mapper-btn json-mapper-btn-danger mapping-delete">Delete</button>' +
      '</div>';
    }).join('');

    container.querySelectorAll('.json-mapper-mapping-row').forEach(row => {
      const id = parseFloat(row.dataset.id);
      const mapping = self.mappings.find(m => m.id === id);

      const sourceSelect = row.querySelector('.mapping-source');
      if (sourceSelect) {
        sourceSelect.addEventListener('change', e => {
          mapping.source = e.target.value;
        });
      }

      const targetSelect = row.querySelector('.mapping-target');
      if (targetSelect) {
        targetSelect.addEventListener('change', e => {
          mapping.target = e.target.value;
        });
      }

      row.querySelector('.mapping-transform').addEventListener('change', e => {
        mapping.transform = e.target.value;
        self.renderIntegrationMappings();
      });

      const paramsInput = row.querySelector('.mapping-params');
      if (paramsInput) {
        paramsInput.addEventListener('input', e => {
          mapping.params = e.target.value.split(',').map(p => p.trim());
        });
      }

      const jsCodeArea = row.querySelector('.mapping-js-code');
      if (jsCodeArea) {
        jsCodeArea.addEventListener('input', e => {
          mapping.jsCode = e.target.value;
        });
      }

      row.querySelectorAll('.json-mapper-source-field-chip').forEach(chip => {
        chip.addEventListener('click', e => {
          const fieldPath = e.target.dataset.field;
          const idx = mapping.sourceFields.indexOf(fieldPath);
          if (idx !== -1) {
            mapping.sourceFields.splice(idx, 1);
          } else {
            mapping.sourceFields.push(fieldPath);
          }
          self.renderIntegrationMappings();
        });
      });

      row.querySelector('.mapping-delete').addEventListener('click', () => {
        self.mappings = self.mappings.filter(m => m.id !== id);
        self.markAsChanged();
        self.renderIntegrationMappings();
      });
    });

    if (this.currentIntegration) {
      this.currentIntegration.mappings = this.mappings;
    }
  }

  // === DATA TRANSFORMATION ===

  getNestedValue(obj, path) {
    return path.split('.').reduce((curr, key) => curr ? curr[key] : undefined, obj);
  }

  setNestedValue(obj, path, value) {
    const keys = path.split('.');
    const lastKey = keys.pop();
    const target = keys.reduce((curr, key) => {
      if (!curr[key]) curr[key] = {};
      return curr[key];
    }, obj);
    target[lastKey] = value;
  }

  testIntegrationMapping() {
    const output = {};
    const preview = document.getElementById('integration-output-preview');
    const self = this;

    try {
      this.mappings.forEach(mapping => {
        if (!mapping.target) return;

        let value;

        if (mapping.transform === 'javascript') {
          if (!mapping.jsCode) return;
          
          const fields = {};
          mapping.sourceFields.forEach(fieldPath => {
            fields[fieldPath] = self.getNestedValue(self.sourceData, fieldPath);
          });

          try {
            const func = new Function('fields', mapping.jsCode);
            value = func(fields);
          } catch (e) {
            throw new Error('JavaScript error in ' + mapping.target + ': ' + e.message);
          }
        } else {
          if (!mapping.source) return;
          
          value = self.getNestedValue(self.sourceData, mapping.source);
          
          if (mapping.transform && mapping.transform !== 'none') {
            const transformFn = self.transformations[mapping.transform].fn;
            value = transformFn.apply(null, [value].concat(mapping.params));
          }
        }

        self.setNestedValue(output, mapping.target, value);
      });

      preview.textContent = JSON.stringify(output, null, 2);
      preview.style.color = '#000';
    } catch (e) {
      preview.textContent = 'Error: ' + e.message;
      preview.style.color = '#dc3545';
    }
  }

  async executeIntegrationApi() {
    if (!this.currentIntegration) {
      alert('Please save the integration to backend first');
      return;
    }

    if (!this.sourceData) {
      alert('Please provide sample source JSON first');
      return;
    }

    const responseContainer = document.getElementById('integration-api-response');
    const sourceType = this.currentIntegration.sourceType;

    if (sourceType === 'webhook') {
      if (!this.webhookUrl) {
        alert('Webhook URL not available');
        return;
      }

      responseContainer.textContent = 'Executing integration...\nSending sample source JSON to webhook endpoint...';
      responseContainer.style.color = '#666';

      try {
        // Send the sample source JSON to the webhook endpoint
        const response = await fetch(this.webhookUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(this.sourceData)
        });

        const responseData = await response.text();

        let parsedResponse;
        try {
          parsedResponse = JSON.parse(responseData);
        } catch (e) {
          parsedResponse = responseData;
        }

        const result = {
          webhook_url: this.webhookUrl,
          source_payload: this.sourceData,
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries()),
          response: parsedResponse
        };

        responseContainer.textContent = JSON.stringify(result, null, 2);
        responseContainer.style.color = response.ok ? '#28a745' : '#dc3545';

      } catch (e) {
        responseContainer.textContent = 'Error: ' + e.message;
        responseContainer.style.color = '#dc3545';
      }

    } else if (sourceType === 'pubsub') {
      // For Pub/Sub, we need to publish a message to test
      responseContainer.textContent = 'Testing Pub/Sub integration...\nPublishing message to Pub/Sub topic...';
      responseContainer.style.color = '#666';

      try {
        // Call backend endpoint to publish test message
        const response = await fetch(`${this.apiBaseUrl}/integrations/${this.integrationId}/test-pubsub/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken()
          },
          body: JSON.stringify({
            message_data: this.sourceData
          })
        });

        const responseData = await response.json();

        const result = {
          source_type: 'pubsub',
          source_payload: this.sourceData,
          status: response.status,
          statusText: response.statusText,
          response: responseData
        };

        responseContainer.textContent = JSON.stringify(result, null, 2);
        responseContainer.style.color = response.ok ? '#28a745' : '#dc3545';

      } catch (e) {
        responseContainer.textContent = 'Error: ' + e.message;
        responseContainer.style.color = '#dc3545';
      }
    }
  }

  // === UTILITY METHODS ===

  loadJsonStrings(sourceJson, targetJson) {
    document.getElementById('integration-source-json').value = sourceJson;
    document.getElementById('integration-target-json').value = targetJson;
    this.loadIntegrationSource();
    this.loadIntegrationTarget();
  }

  exportConfiguration() {
    if (!this.currentIntegration) {
      alert('No integration to export');
      return;
    }

    const config = this.serializeIntegration();
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'integration-' + config.name.replace(/\s+/g, '-').toLowerCase() + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  importConfiguration(file) {
    const reader = new FileReader();
    const self = this;
    
    reader.onload = function(event) {
      try {
        const config = JSON.parse(event.target.result);
        
        document.getElementById('integration-name').value = config.name;
        document.getElementById('source-type').value = config.sourceType;
        self.updateSourceConfig(config.sourceType);
        
        if (config.sourceType === 'webhook' && config.sourceConfig.webhookUrl) {
          document.getElementById('webhook-url').value = config.sourceConfig.webhookUrl;
        } else if (config.sourceType === 'pubsub') {
          document.getElementById('pubsub-project').value = config.sourceConfig.projectId || '';
          document.getElementById('pubsub-subscription').value = config.sourceConfig.subscription || '';
        }

        document.getElementById('integration-method').value = config.target.method;
        document.getElementById('integration-url').value = config.target.url;
        document.getElementById('integration-auth').value = config.target.authType;
        self.updateIntegrationAuthConfig(config.target.authType);

        if (config.target.authType === 'bearer') {
          document.getElementById('integration-bearer-token').value = config.target.auth.token || '';
        } else if (config.target.authType === 'basic') {
          document.getElementById('integration-basic-username').value = config.target.auth.username || '';
          document.getElementById('integration-basic-password').value = config.target.auth.password || '';
        } else if (config.target.authType === 'apikey') {
          document.getElementById('integration-apikey-header').value = config.target.auth.headerName || '';
          document.getElementById('integration-apikey-value').value = config.target.auth.apiKey || '';
        }

        const headersText = Object.entries(config.target.headers || {})
          .map(([k, v]) => k + ': ' + v)
          .join('\n');
        document.getElementById('integration-headers').value = headersText;

        self.mappings = config.mappings || [];
        
        alert('Configuration imported successfully!');
        
      } catch (error) {
        alert('Error importing configuration: ' + error.message);
      }
    };
    
    reader.readAsText(file);
  }
}

// Export for use in browser
if (typeof window !== 'undefined') {
  window.JSONMapper = JSONMapper;
}