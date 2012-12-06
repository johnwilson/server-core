$(function(){
    var Command = Backbone.Model.extend({
        defaults: {
            name:"",
            request:"",
            response:"",
            response_raw:""
        },
        
        addResponse: function(response){
            this.set({ response: response });
        }
    });
    
    var CommandHistory = Backbone.Collection.extend({
        model: Command
    });
    
    //--------------------------------------------------------------------------
    //  Application Views and widgets
    //--------------------------------------------------------------------------
    
    var ResponseErrorView = Backbone.View.extend({
        tagName: "div",
        
        //cache template
        template: _.template($("#template_error").html()),
        
        render: function(){
            var response = this.model.get("response");
            var _renderdata = {title:"Error",message:response.msg}
            this.$el.html(this.template(_renderdata));
            return this;
        }
    });
    
    var CommandView = Backbone.View.extend({
        tagName: "section",
        
        //cache template
        template: _.template($("#template_ctrlCommand").html()),
        
        initialize: function(){
            this.model.bind("change:response", this.render, this);            
        },
        
        render: function(){
            var _response = this.model.get("response");
            if(_response.hasOwnProperty("status") )
            {
                if(_response.status == "error")
                {
                    this.render_error();
                }
                else
                {
                    this.render_response();
                }
            }
            else
            {
                this.$el.html(this.template(this.model.toJSON()));
            }
            
            return this;
        },
        render_error: function(){
            var _view = new ResponseErrorView({model:this.model});            
            this.$el.append(_view.render().el);            
            terminal.commandcompleted(true);
        },
        render_response: function(){
            var _renderdata = this.model.get("response");
            var _renderdata_raw = this.model.get("response_raw");
            var _template = "";
            switch(_renderdata.command){
                case "help *":
                    _template = _.template($("#template_helpall").html(), _renderdata)                   
                    break;
                case "help":
                    _template = _.template($("#template_help").html(), _renderdata)                   
                    break;
                case "login":
                    ticket = _renderdata.data.ticket;
                    _template = _.template($("#template_info").html(), {data:"You are now logged into Bytengine!"})
                    break;
                default:
                    _renderdata = {data:_renderdata_raw};
                    _template = _.template($("#template_command_response").html(), _renderdata)
                    break;
            }
            
            this.$el.append(_template);            
            terminal.commandcompleted(false);
        }
    });
    
    var TerminalView = Backbone.View.extend({
        el: $("#ctrlTerminal"),
        initialize: function(){
            this.render();
            this.codeMirrorObj = null;
        },
        render: function(event){
            this.$el.html($("#template_ctrlTerminal").html());            
            return this;
        },
        events: {
            "click #btnRunCommand": "runcommand",
            "click #btnClearScreen": "clearconsole",
            "click #btnUndockInputBox": "undockinput"
        },
        runcommand: function(event){
            event.preventDefault();
            var request_text = $.trim(this.$("#ctrlInputBox").val());
            
            // create command control and add to screen
            var _command = new Command({request:request_text,_id:commandHistory.length})
            
            // check if request is sensitive info
            var command_parts = request_text.split(' ',1);
            if(command_parts.length > 0 & command_parts[0] == "login")
            {
                var _command = new Command({request:"login ...",_id:commandHistory.length})
                // use usermode by default
                request_text += " --usermode";
            }
            else
            {
                var _command = new Command({request:request_text,_id:commandHistory.length})
            }
            
            commandHistory.push(_command);
            var _commmandView = new CommandView({model:_command});
            this.$("#ctrlScreen").append(_commmandView.render().el);
            
            // create post data
            var postdata = {command:request_text,ticket:ticket,prettyprint:true};
            
            // make ajax call to server
            $.ajax({
                type:'POST',
                url: '/bfs/formatted',
                data: postdata,
                async:false,
                dataType:'text',
                success: function(data)
                {
                    _raw = data;
                    _json = $.parseJSON(data)
                    index = commandHistory.length -1;
                    var _command = commandHistory.at(index);                    
                    _command.set({response_raw:_raw});
                    _command.set({response:_json});
                },
                error: function(jqXHR, textStatus, errorThrown){
                    var _json = {
                        status:"error",
                        msg:"Terminal Application Error!<br/>",
                        code:textStatus,type:"terminal_application_error"
                    };
                    if(jqXHR.responseText){
                        _json.msg += jqXHR.responseText;
                    }
                    else{
                        _json.msg += errorThrown;
                    }
                    index = commandHistory.length -1;
                    var _command = commandHistory.at(index);                    
                    _command.set({response_raw:""});
                    _command.set({response:_json});
                }
            });
            
            // on response update command control by calling response render function
            
            // if error do not clear input, if success clear input and focus
            
            return false;
        },
        clearconsole: function(event){
            event.preventDefault();
            // clear screen and command history
            this.$("#ctrlScreen").empty();
            return false;
        },
        undockinput: function(event){
            event.preventDefault();
            
            var commandTxt = $('#ctrlInputBox').val();
            expanded_editor.setValue(commandTxt);
            
            $('#expanded_input').on('shown', function(){
                expanded_editor.refresh();
                expanded_editor.focus();
            });
            
            $('#expanded_input').on('hide', function(){
                expanded_editor.setValue("");
                expanded_editor.refresh();
            });
            
            $('#expanded_input').modal({show:true});
            
        },        
        commandcompleted: function(iserror){
            // scroll to bottom
            var _height = this.$("#ctrlScreen")[0].scrollHeight;
            this.$("#ctrlScreen").animate({scrollTop: _height}, 1000);
            
            if(iserror == false)
            {
                // clear input and give focus to control
                this.$("#ctrlInputBox").val('');
                this.$("#ctrlInputBox").focus();                
            }           
        },
        autocompleteupdate: function(data){
            //this.$("#ctrlInputBox").autocomplete({lookup:data.core});
        }
    });
    
    // Launch Application
    var ticket = null;
    var commandHistory = new CommandHistory();
    var terminal = new TerminalView();
    
    // setup code mirror
    var expanded_editor = CodeMirror.fromTextArea(document.getElementById("codemirrorTextarea"), {
        lineNumbers: false,
        matchBrackets: true,
        mode: {name: "javascript", json: true},
        smartIndent: true,
        indentWithTabs: true,
        tabSize: 2
    });
    
    // setup popup button save
    $("#btnCodeMirrorSave").click(function(){
        commandTxt = expanded_editor.getValue();
        $('#ctrlInputBox').val(commandTxt);
        $('#expanded_input').modal('hide');
        $("#ctrlInputBox").focus();
    });
    
    // get list of commands
    // make ajax call to server
    $.ajax({
        type:'POST',
        url: '/bfs/formatted',
        data: {command:"help *"},
        async:false,
        dataType:'json',
        success: function(data)
        {
            terminal.autocompleteupdate(data.data);
        },
        error: function(data)
        {
            console.log(data);
        }
    });
});
