frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Workflow',
                name: 'Material Request Approval'
            },
            callback: function(workflow) {
                if (workflow.message && workflow.message.states) {
                    const states = workflow.message.states;
                    
                    // Create a mapping of states to their properties
                    const stateMap = {};
                    states.forEach((state, index) => {
                        stateMap[state.state] = {
                            color: state.style || state.state,
                            progress: ((index + 1) / states.length) * 100,
                            index: index
                        };
                    });
                    
                    if (frm.doc.workflow_state && stateMap[frm.doc.workflow_state]) {
                        const currentState = stateMap[frm.doc.workflow_state];
                        
                        // Add progress bar with state-specific color
                        frm.dashboard.add_progress(
                            `Workflow Progress: ${frm.doc.workflow_state}`,
                            currentState.progress,
                            currentState.color
                        );
                        
                        // Optional: Add indicator
                        // frm.page.set_indicator(frm.doc.workflow_state, currentState.color.toLowerCase());
                    }
                }
            }
        });
    }
});