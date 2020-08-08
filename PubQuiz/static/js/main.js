function set_pending(q_elem) {
    if (q_elem.className != 'answer pending') {
        q_elem.className = 'answer pending';
        q_elem.insertAdjacentHTML('afterend', loading_icon);
    }
}

function unset_pending(q_elem) {
    q_elem.className = 'answer';
    var loading = q_elem.nextSibling;
    if (loading !== null && loading.className == 'loading') {
        loading.parentNode.removeChild(loading);
    }
}

function update_view() {
    var view_req = new XMLHttpRequest();
    view_req.open('GET', '/quiz_view', true);
    view_req.onreadystatechange= function() {
        if (this.readyState!==4) return;
        if (this.status!==200) {
            document.getElementById('quiz_view').innerHTML = 'Connection error';
            return;
        }

        // Store current answers before update
        var ans_elems = document.getElementsByClassName('answer');
        var ans_vals = new Array(ans_elems.length);
        for (var i=0; i<ans_elems.length; i++) {
            if (ans_elems[i].type == 'radio') {
                ans_vals[i] = ans_elems[i].checked;
            } else {
                ans_vals[i] = ans_elems[i].value;
            }
        }


        // Store current selection before update.
        var old_act = document.activeElement;
        var is_active = old_act.id !== '';
        if (is_active) {
            var act_id = old_act.id;
            var act_sel_s = old_act.selectionStart;
            var act_sel_e = old_act.selectionEnd;
        }

        // Update view
        var el = document.createElement('html');
        el.innerHTML = this.responseText;
        var answers = el.getElementsByClassName('answer');
        if (answers.length < 1 || answers.length != document.getElementsByClassName('answer').length ) {
            if (this.responseText === 'NOLOGIN') {
                // Login is invalid, redirect to login page
                window.location.replace('/login');
            } else{
                document.getElementById('quiz_view').innerHTML = this.responseText;
            }
        } else {
            // Avoid replacing entire HTML while user might be typing an answer
            for (var i=0; i<ans_vals.length; i++) {
                ans_elems[i].value = answers[i].value;
            }
            document.getElementsByClassName('player_list')[0].innerHTML = el.getElementsByClassName('player_list')[0].innerHTML;
        }

        // Restore current answers
        var ans_elems = document.getElementsByClassName('answer');
        for (var i=0; i<ans_vals.length; i++) {
            var pending

            if (ans_elems[i].type == 'radio') {
                pending = ans_vals[i] !== ans_elems[i].checked;
                ans_elems[i].checked = ans_vals[i];
            } else {
                pending = ans_vals[i] !== ans_elems[i].value;
                ans_elems[i].value = ans_vals[i];
            }

            if (pending) {
                set_pending(ans_elems[i]);
            } else {
                unset_pending(ans_elems[i]);
            }
            ans_elems[i].addEventListener('input', function(){
                set_pending(this);
            }.bind(ans_elems[i]));
        }

        // Restore selection
        if (is_active) {
            var new_act = document.getElementById(act_id);
            new_act.focus();
            new_act.selectionStart = act_sel_s;
            new_act.selectionEnd = act_sel_e;
        }

    };

    var post_req = new XMLHttpRequest();
    post_req.open('POST', '/quiz_endpoint', true);
    post_req.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    post_req.onreadystatechange = function() {
        if (this.status !== 200) {
            console.log('POST request failed');
            return;
        }
    };

    var post_string = ''
    var answers = document.getElementsByClassName('answer');
    for (var i=0; i<answers.length; i++) {
        var ans = answers[i];
        if (ans.type == 'text' || (ans.type == 'radio' && ans.checked)){
            post_string += ans.name + '=' + encodeURIComponent(ans.value);
            console.log(ans.type);
            console.log(ans.value);
            if (i < answers.length -1) {
                post_string += '&';
            }
        }
    }

    post_req.send(post_string);
    view_req.send();
}

update_view();
setInterval(update_view, 1000);