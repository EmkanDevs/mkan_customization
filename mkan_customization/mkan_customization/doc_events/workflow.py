import frappe

def before_validate(self, method):
    if self.is_active and self.track_state_transitions:
        meta = frappe.get_meta(self.document_type)

        last_field = meta.fields[-1].fieldname if meta.fields else None

        Progress = "workflow_progress"
        html_field_name = "custom_html"
        state_change_field_name = "state_change"
        fieldnames = [df.fieldname for df in meta.get("fields")]

        if Progress not in fieldnames:
            custom_progress_field = frappe.new_doc("Custom Field")
            custom_progress_field.dt = self.document_type  
            custom_progress_field.fieldname = Progress
            custom_progress_field.label = "Progress"
            custom_progress_field.fieldtype = "Tab Break"
            custom_progress_field.insert_after = last_field  
            custom_progress_field.insert()
            frappe.msgprint(f"Created {Progress} field.")  


        if html_field_name not in fieldnames:
            custom_html_field = frappe.new_doc("Custom Field")
            custom_html_field.dt = self.document_type  
            custom_html_field.fieldname = html_field_name
            custom_html_field.label = "HTML"
            custom_html_field.fieldtype = "HTML"
            custom_html_field.insert_after = Progress  
            custom_html_field.insert()
            frappe.msgprint(f"Created {html_field_name} field.")  

        if state_change_field_name not in fieldnames:
            custom_state_change_field = frappe.new_doc("Custom Field")
            custom_state_change_field.dt = self.document_type  
            custom_state_change_field.fieldname = state_change_field_name
            custom_state_change_field.label = "State Change"
            custom_state_change_field.fieldtype = "Table" 
            custom_state_change_field.options = "State Change Items"  
            custom_state_change_field.insert_after = html_field_name  
            custom_state_change_field.insert()
            frappe.msgprint(f"Created {state_change_field_name} field.")  

        frappe.db.commit()  
        client_script_name = f"{self.document_type}-State Change"

        if frappe.db.exists("Client Script", client_script_name):
            frappe.delete_doc("Client Script", client_script_name)

        client_script = frappe.new_doc("Client Script")
        client_script.dt = self.document_type
        client_script.script_type = "Client"
        client_script.enabled = 1
        client_script.name = client_script_name
        client_script.script = f"""
            frappe.ui.form.on('{self.document_type}', {{
                onload: function (frm) {{
                    function generateStatusIndicators(state_change, workflowStates, options = {{}}) {{
                        const config = {{
                            completedMarker: '✓',
                            currentMarker: '?',
                            rejectedMarker: '✗',
                            emptyMarker: '',
                            rejectedKeywords: ['reject', 'canceled', 'declined'],
                            ...options
                        }};

                        const stateOrder = workflowStates.map(state => typeof state === 'object' ? state.state : state);
                        return state_change.map(row => {{
                            const currentStateIndex = stateOrder.findIndex(state => state.toLowerCase() === (row.workflow_state || '').toLowerCase());
                            const isRejected = config.rejectedKeywords.some(keyword => (row.workflow_state || '').toLowerCase().includes(keyword));

                            return stateOrder.map((state, stateIndex) => {{
                                if (stateIndex < currentStateIndex) return config.completedMarker;
                                if (isRejected) return stateIndex === currentStateIndex ? config.rejectedMarker : config.emptyMarker;
                                if (stateIndex === currentStateIndex) return config.currentMarker;
                                return config.emptyMarker;
                            }});
                        }});
                    }}

                    function fetchWorkflowDetails() {{
                        return frappe.call({{
                            method: 'workflow_transitions.workflow_transitions.doc_events.workflow.get_workflow_fields',
                            args: {{ doc: "{self.document_type}" }}
                        }}).then(r => {{
                            if (r.message && r.message.length > 0) {{
                                return r.message.map(workflow => ({{
                                    state: workflow.state || "",
                                    roles: workflow.allow_edit ? [workflow.allow_edit] : []
                                }}));
                            }} else {{
                                console.warn("No active workflow found!");
                                return Promise.reject(new Error('No active workflow found'));
                            }}
                        }}).catch(err => {{
                            console.error("Workflow Fetch Error:", err);
                            return Promise.reject(err);
                        }});
                    }}

                    function getCurrentState(frm) {{
                        if (frm.doc.workflow_state) {{
                            return frm.doc.workflow_state;
                        }}

                        if (frm.doc.state_change && frm.doc.state_change.length > 0) {{
                            return frm.doc.state_change[frm.doc.state_change.length - 1].workflow_state || 'Draft';
                        }}

                        return 'Draft';
                    }}

                    function createWorkflowVisualization(workflowStates, currentState) {{
                        const uniqueRoles = [...new Map(workflowStates.map(state => [state.roles[0], state.roles[0]])).values()];

                        const statusIndicators = generateStatusIndicators(frm.doc.state_change, workflowStates, {{
                            currentMarker: '?',
                            completedMarker: '✓',
                            rejectedMarker: '✗'
                        }});

                        const levelBoxes = uniqueRoles.map((role, index) => {{
                            const roleStateIndex = workflowStates.findIndex(state => state.roles.includes(role));
                            const marker = roleStateIndex !== -1 ? statusIndicators[0][roleStateIndex] : '';

                            return `
                                <div class="level-box" style="
                                    position: relative;
                                    padding: 10px;
                                    border: 2px solid blue;
                                    border-radius: 5px;
                                    margin: 0 10px;
                                    flex: 1;
                                    min-width: 100px;
                                    text-align: center;
                                ">
                                    <div style="
                                        position: absolute;
                                        top: 5px;
                                        right: 5px;
                                        font-weight: bold;
                                        font-size: 24px;
                                        color: ${{marker === '✓' ? 'green' : marker === '?' ? 'orange' : marker === '✗' ? 'red' : 'blue'}}
                                    ">
                                        ${{marker}}
                                    </div>
                                    <label style="display: block; margin-top: 20px;">
                                        <strong>${{role}}</strong><br>
                                        Level ${{index + 1}}
                                    </label>
                                </div>
                            `;
                        }}).join('');

                        return `
                            <div style="text-align: center; margin-bottom: 15px;">
                                <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                                    ${{levelBoxes}}
                                </div>
                            </div>
                        `;
                    }}

                    function updateCustomHtml() {{
                        const currentState = getCurrentState(frm);
                        fetchWorkflowDetails().then(workflowStates => {{
                            const htmlContent = createWorkflowVisualization(workflowStates, currentState);
                            if (frm.fields_dict.custom_html) {{
                                console.log("Updating custom_html field...");
                                $(frm.fields_dict.custom_html.wrapper).html(htmlContent);
                            }} else {{
                                console.warn("custom_html field not found in the form!");
                            }}
                        }}).catch(err => {{
                            console.log("Error processing workflow");
                        }});
                    }}

                    updateCustomHtml();

                    frm.events.refresh = function (frm) {{
                        frm.add_custom_button(__('Refresh Workflow'), function () {{
                            updateCustomHtml();
                        }});
                    }};
                }}
            }});
        """
        client_script.insert()
        frappe.db.commit()  