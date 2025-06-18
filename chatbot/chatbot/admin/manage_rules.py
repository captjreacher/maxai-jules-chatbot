{% extends "admin/admin_layout.html" %}
{% block admin_content %}
    <h3>{{ 'Edit Rule: ' + form_data.Rule_ID if edit_mode else 'Add New Rule' }}</h3>
    <form method="POST" action="{{ url_for('admin.manage_rules', edit_rule_id=form_data.Rule_ID if edit_mode else None) }}" style="margin-bottom: 30px; padding: 15px; border: 1px solid #eee; border-radius: 5px;">

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; margin-bottom: 10px;">
            <div>
                <label for="rule_id" style="display: block; margin-bottom: 5px;">Rule ID (unique, required):</label>
                <input type="text" id="rule_id" name="rule_id" value="{{ form_data.Rule_ID if form_data else '' }}" style="width: 95%; padding: 8px; border: 1px solid #ccc; border-radius: 3px;" required {% if edit_mode %}readonly{% endif %}>
                {% if edit_mode %}<small style="display: block; margin-top: 4px;">To change ID, delete and re-add the rule.</small>{% endif %}
            </div>
            <div>
                <label for="context_required" style="display: block; margin-bottom: 5px;">Context Required (optional):</label>
                <input type="text" id="context_required" name="context_required" value="{{ form_data.Context_Required if form_data else '' }}" style="width: 95%; padding: 8px; border: 1px solid #ccc; border-radius: 3px;">
            </div>
            <div>
                <label for="pattern" style="display: block; margin-bottom: 5px;">Pattern (user input, or blank if context-only trigger):</label>
                <input type="text" id="pattern" name="pattern" value="{{ form_data.Pattern if form_data else '' }}" style="width: 95%; padding: 8px; border: 1px solid #ccc; border-radius: 3px;">
            </div>
            <div>
                <label for="set_context_on_response" style="display: block; margin-bottom: 5px;">Set Context on Response (optional, or 'CLEAR'):</label>
                <input type="text" id="set_context_on_response" name="set_context_on_response" value="{{ form_data.Set_Context_On_Response if form_data else '' }}" style="width: 95%; padding: 8px; border: 1px solid #ccc; border-radius: 3px;">
            </div>
            <div>
                <label for="go_to_rule_id" style="display: block; margin-bottom: 5px;">GoTo Rule ID (optional, for chaining):</label>
                <input type="text" id="go_to_rule_id" name="go_to_rule_id" value="{{ form_data.GoTo_Rule_ID if form_data else '' }}" style="width: 95%; padding: 8px; border: 1px solid #ccc; border-radius: 3px;">
            </div>
        </div>
        <div style="margin-bottom: 10px;">
            <label for="response" style="display: block; margin-bottom: 5px;">Response (chatbot output, can be blank if GoTo used):</label>
            <textarea id="response" name="response" rows="4" style="width: 98%; padding: 8px; border: 1px solid #ccc; border-radius: 3px;">{{ form_data.Response if form_data else '' }}</textarea>
        </div>
        <div>
            <input type="submit" name="action" value="{{ 'Update Rule' if edit_mode else 'Add Rule' }}" style="padding: 8px 15px; background-color: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer;">
            {% if edit_mode %}
                <a href="{{ url_for('admin.manage_rules') }}" style="margin-left: 10px; text-decoration: none; padding: 8px 15px; background-color: #6c757d; color: white; border-radius: 3px;">Cancel Edit</a>
            {% endif %}
        </div>
    </form>

    <h3>Current Rules</h3>
    <p><small>Rules File Path: {{ RULES_CSV_FILE_PATH_DISPLAY if RULES_CSV_FILE_PATH_DISPLAY else "Path not set" }}</small></p>
    {% if rules %}
        <div style="overflow-x: auto;">
            <table style="width: 100%; min-width: 900px; border-collapse: collapse; font-size: 0.9em;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="border: 1px solid #ddd; padding: 6px; text-align: left;">ID</th>
                        <th style="border: 1px solid #ddd; padding: 6px; text-align: left;">Context Req.</th>
                        <th style="border: 1px solid #ddd; padding: 6px; text-align: left;">Pattern</th>
                        <th style="border: 1px solid #ddd; padding: 6px; text-align: left;">Response (preview)</th>
                        <th style="border: 1px solid #ddd; padding: 6px; text-align: left;">Set Context</th>
                        <th style="border: 1px solid #ddd; padding: 6px; text-align: left;">GoTo ID</th>
                        <th style="border: 1px solid #ddd; padding: 6px; text-align: left;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for rule in rules %}
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 6px;">{{ rule.Rule_ID }}</td>
                        <td style="border: 1px solid #ddd; padding: 6px;">{{ rule.Context_Required }}</td>
                        <td style="border: 1px solid #ddd; padding: 6px; white-space: pre-wrap; word-break: break-all;">{{ rule.Pattern }}</td>
                        <td style="border: 1px solid #ddd; padding: 6px; white-space: pre-wrap; word-break: break-all;">{{ rule.Response[:100] }}{% if rule.Response|length > 100 %}...{% endif %}</td>
                        <td style="border: 1px solid #ddd; padding: 6px;">{{ rule.Set_Context_On_Response }}</td>
                        <td style="border: 1px solid #ddd; padding: 6px;">{{ rule.GoTo_Rule_ID }}</td>
                        <td style="border: 1px solid #ddd; padding: 6px; white-space: nowrap;">
                            <a href="{{ url_for('admin.manage_rules', edit_rule_id=rule.Rule_ID) }}" style="margin-right: 8px; text-decoration: none; color: #007bff;">Edit</a>
                            <form method="POST" action="{{ url_for('admin.delete_rule', rule_id=rule.Rule_ID) }}" style="display: inline;" onsubmit="return confirm('Are you sure you want to delete rule {{rule.Rule_ID}}?');">
                                <input type="submit" value="Delete" style="background: none; border: none; color: #dc3545; cursor: pointer; padding: 0; text-decoration: underline; font-size: inherit;">
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    {% else %}
        <p>No rules found or an error occurred reading the rules file. Check server logs.</p>
        <p>Ensure your <code>rules.csv</code> file exists at the expected path, is readable, and has the correct 6-column headers: <br><code>Rule_ID,Context_Required,Pattern,Response,Set_Context_On_Response,GoTo_Rule_ID</code></p>
        <p>(Add a rule using the form above or upload a correctly formatted CSV file.)</p>
    {% endif %}

    <hr style="margin-top: 30px; margin-bottom: 30px;">

    <h3>Upload Rules File (CSV)</h3>
    <p>This will <strong>replace</strong> all current rules. The CSV file's first row must contain these exact headers: <br><code>Rule_ID,Context_Required,Pattern,Response,Set_Context_On_Response,GoTo_Rule_ID</code></p>
    <form method="POST" action="{{ url_for('admin.upload_rules_file') }}" enctype="multipart/form-data" style="padding: 15px; border: 1px solid #eee; border-radius: 5px;">
        <div style="margin-bottom: 10px;">
            <label for="rules_file" style="display: block; margin-bottom: 5px;">Select CSV file:</label>
            <input type="file" id="rules_file" name="rules_file" accept=".csv" required>
        </div>
        <div>
            <input type="submit" value="Upload and Replace Rules" style="padding: 8px 15px; background-color: #28a745; color: white; border: none; border-radius: 3px; cursor: pointer;">
        </div>
    </form>
{% endblock %}