var ActiveConnections = {};

function BytengineConnector(options){
    this.username = options.username;
    this.password = options.password;
    this.database = options.database;
    this.mode = options.mode || "application";
    this.ticket = "";    
}

BytengineConnector.prototype.connect = function(){
    var command = "login -u='" + this.username +"' -p='" + this.password +"' -d='" +
                  this.database + "'";
    if(this.mode == "usermode"){
        command += " --usermode";
    }
    
    var _postdata = {
        command:command,
        ticket:null,
        prettyprint:false
    };
    
    $.ajax({
        url: "/bfs",
        type: "POST",
        data: _postdata,
        dataType: "json",
        async: false,
        context: this,
        success: function(response){
            if(response.status != "ok"){
                throw response.msg;
            }
            this.ticket = response.data.ticket;
        },
        error: function(error){
            throw "Connection to Bytengine failed.";
        }
    });
};

BytengineConnector.prototype.command = function(options){
    var _postdata = {
        command:options.command,
        ticket:this.ticket,
        prettyprint:false
    };
    
    $.ajax({
        url: "/bfs",
        type: "POST",
        data: _postdata,
        context: this,
        dataType: "json",
        success: function(response){
            if(response.status == "ok"){
                if(options.onSuccess){
                    options.onSuccess(response);
                }                        
            }
            else{
                if(response.code == "BE105"){
                    this.connect();
                    // recursion
                    this.command(options);
                }
                else{
                    if(options.onError){
                        options.onError(response.msg);
                    }
                }
            }
        },
        error: function(jqXHR, textStatus, errorThrown){
            if(jqXHR.responseText){
                if(options.onError){
                    options.onError(jqXHR.responseText);
                }                        
            }
            else{
                if(options.onError){
                    options.onError(jqXHR.responseText);
                }
            }
        }
    });
};


function Editor(options){
    this.attachment = null;
    this.file = null;
    this.editorMode = {name: "javascript", json: true};
    this.fileCodeEditor = null;
    this.attachmentCodeEditor = null;
    this.currentview = "empty"; // empty | file | attachment | upload
    this.loaderControl = options.loaderControl || null;
    
    // tab controls
    $('#ide_tab_ctrl a[href="#filecontent_tab"]').bind("click", {view:this}, function(event){
        event.preventDefault();
        event.data.view.currentview = "file";
        $(this).tab('show');
    });
    
    $('#ide_tab_ctrl a[href="#attachment_tab"]').bind("click", {view:this}, function(event){
        event.preventDefault();
        event.data.view.currentview = "attachment";
        $(this).tab('show');
    });
    
    // bind buttons and menu items
    $("#menu_btn_reload, #menu_link_reload").bind("click", {view:this}, function(event){
        event.preventDefault();
        if(event.data.view.file == null){ return; }
        switch(event.data.view.currentview){
            case "file":
                event.data.view.loaderControl.reloadFile({
                    file: event.data.view.file,
                    onSuccess: function(data){
                        event.data.view.refresh();
                    },
                    onError: function(error){
                        event.data.view.notifyError(error);
                    }
                });
                break;
            case "attachment":
                event.data.view.loaderControl.loadAttachment({
                    file: event.data.view.file,
                    onError: function(error){
                        event.data.view.notifyError(error);
                    }
                });
                break;
            default:
                break;
        }
    });
    
    $("#menu_link_save, #menu_btn_save").bind("click", {view:this}, function(event){
        event.preventDefault();
        if(event.data.view.file == null){ return; }
        switch(event.data.view.currentview){
            case "file":
                event.data.view.file.data = event.data.view.fileCodeEditor.getValue();
                var _postdata = event.data.view.file.postdata;
                _postdata.data = event.data.view.file.data;
                
                $.ajax({
                    url: "/ui/ide/save/file",
                    type: "POST",
                    context: event.data.view,
                    data: _postdata,
                    dataType: "json",
                    success: function(response, textStatus, jqXHR){
                        if(response.status == "ok"){
                            this.notifySuccess("File saved.");
                        }
                        else{
                            this.notifyError(response.msg);
                        }
                        this.fileCodeEditor.focus();
                    },
                    error: function(jqXHR, textStatus, errorThrown){
                        if(jqXHR.responseText){
                            this.notifyError(jqXHR.responseText);
                        }
                        else{
                            this.notifyError(errorThrown);
                        }
                        this.fileCodeEditor.focus();
                    }
                });
                break;
            case "attachment":
                var _postdata = event.data.view.file.postdata;
                _postdata.data = event.data.view.attachmentCodeEditor.getValue();
                
                $.ajax({
                    url: "/ui/ide/save/attachment",
                    type: "POST",
                    data: _postdata,
                    context: event.data.view,
                    dataType: "json",
                    success: function(response, textStatus, jqXHR){
                        if(response.status == "ok"){
                            this.notifySuccess("Attachment saved.");
                        }
                        else{
                            this.notifyError(response.msg);
                        }
                        this.attachmentCodeEditor.focus();
                    },
                    error: function(jqXHR, textStatus, errorThrown){
                        if(jqXHR.responseText){
                            this.notifyError(jqXHR.responseText);
                        }
                        else{
                            this.notifyError(errorThrown);
                        }
                        this.attachmentCodeEditor.focus();
                    }
                });
                break;
            default:
                break;
        }
    });
    
    $("#menu_btn_close, #menu_link_close").bind("click", {view:this}, function(event){
        event.preventDefault();
        if(event.data.view.file == null){ return; }
        switch(event.data.view.currentview){
            case "file":
                event.data.view.loaderControl.closeFile(event.data.view.file);
                event.data.view.currentview = "empty";
                event.data.view.refresh();
                break;
            case "attachment":
                var _html = '<div class="centered span6 align_center m-t-80">';
                _html += '<h3>No Content Loaded</h3>';
                _html += '</div>';
                $("#editor_attachment").empty();
                $("#editor_attachment").html(_html);
                event.data.view.attachment = null;
                event.data.view.attachmentCodeEditor = null;                
                event.data.view.currentview = "file";
                event.data.view.refresh();
                break;
            default:
                break;
        }
    });
    
    $("#menu_link_makepublic").bind("click", {view:this}, function(event){
        event.preventDefault();
        if(event.data.view.file == null){ return; }
        event.data.view.updateFileAccess("public");
    });
    
    $("#menu_link_makeprivate").bind("click", {view:this}, function(event){
        event.preventDefault();
        if(event.data.view.file == null){ return; }
        event.data.view.updateFileAccess("private");
    });
    
    $("#menu_link_attch_open").bind("click", {view:this}, function(event){
        event.preventDefault();
        if(event.data.view.file == null){ return; }
        event.data.view.loaderControl.loadAttachment({
            file: event.data.view.file,
            onError: function(error){
                event.data.view.notifyError(error);
            }
        });
    });
    
    $("#menu_link_attch_new").bind("click", {view:this}, function(event){
        event.preventDefault();
        if(event.data.view.file == null){
            return;
        }
        event.data.view.attachment = "";
        event.data.view.currentview = "attachment";
        event.data.view.refresh();
    });
    
    // editor syntax highlighting mode
    $(".menu_link_ide_mode").bind("click", {view:this}, function(event){
        event.preventDefault();
        if(event.data.view.file == null ||
           event.data.view.currentview != "attachment"){ return; }
        var _mode = $(this).text().toLowerCase();
        event.data.view.changeEditorMode(_mode);
        event.data.view.attachmentCodeEditor.setOption("mode",event.data.view.editorMode);
    });
    
    // event listeners
    $(this.loaderControl).bind("ideEditSelectedFile", {view:this}, function(event, file){
        event.data.view.currentview = "empty";
        event.data.view.refresh();
        
        event.data.view.file = file;
        event.data.view.currentview = "file";
        event.data.view.refresh();
    });
    
    $(this.loaderControl).bind("ideEditSelectedAttachment", {view:this}, function(event, editorMode, data){
        event.data.view.currentview = "attachment";
        event.data.view.changeEditorMode(editorMode);
        event.data.view.attachment = data;
        event.data.view.refresh();
    });
}

Editor.prototype.changeEditorMode = function(mode){
    switch(mode){
        case "jinja2":
            this.editorMode = {name: "jinja2", htmlMode: true};
            break;
        case "css":
            this.editorMode = {name: "css"};
            break;
        case "html":
            this.editorMode = "text/html";
            break;
        case "javascript":
            this.editorMode = {name: "javascript"};
            break;
        default:
            this.editorMode = {name: "javascript", json: true};
            break;
    }
};

Editor.prototype.updateFileAccess = function(access){
    // check active connections
    if(this.file.postdata.username in ActiveConnections){
        var connection = ActiveConnections[this.file.postdata.username]
    }
    else{
        var connection = new BytengineConnector({username:this.file.postdata.username,
                                                 password: this.file.postdata.password,
                                                 database: this.file.postdata.database})
        try{
            connection.connect();
            ActiveConnections[this.file.postdata.username] = connection;
        }
        catch(error){
            this.notifyError(error);
        }
    }
    
    var context = this;
    var cmd = {
        command:"mk" + access + " '" + context.file.postdata.filepath + "'",
        onSuccess: function(response){
            context.notifySuccess(response.data);
        },
        onError: function(error){
            context.notifyError(error);
        }
    };
    connection.command(cmd);
};

Editor.prototype.refresh = function(){
    switch(this.currentview){
        case "file":
            this.currentview = "file";
            $('#ide_tab_ctrl a[href="#filecontent_tab"]').tab("show");
            $("#ide_status_message").text(this.file.postdata.database + ":" + this.file.path_long);
            //$(".currently_editing").text("File Content");
            if(this.fileCodeEditor == null){
                $("#editor_file").empty();
                this.fileCodeEditor = CodeMirror(document.getElementById("editor_file"),{
                    value: this.file.data,
                    mode: {name: "javascript", json: true},
                    smartIndent: true,
                    indentWithTabs: true,
                    tabSize: 2,
                    lineNumbers: true
                });
                $("#editor_file .CodeMirror").css("background","none repeat scroll 0 0 #E1E8ED");
            }
            else{
                $("#editor_file .CodeMirror").css("background","none repeat scroll 0 0 #E1E8ED");
                this.fileCodeEditor.setValue("");
                this.fileCodeEditor.setOption("mode",{name: "javascript", json: true});
                this.fileCodeEditor.setValue(this.file.data);
            }            
            this.fileCodeEditor.focus();
            break;
        case "attachment":
            this.currentview = "attachment";
            $('#ide_tab_ctrl a[href="#attachment_tab"]').tab("show");
            if(this.attachmentCodeEditor == null){
                $("#editor_attachment").empty();
                this.attachmentCodeEditor = CodeMirror(document.getElementById("editor_attachment"),{
                    value: this.attachment,
                    mode: this.editorMode,
                    smartIndent: true,
                    indentWithTabs: true,
                    tabSize: 2,
                    lineNumbers: true
                });
                $("#editor_attachment .CodeMirror").css("background","none repeat scroll 0 0 #FFFFFF");
            }
            else{
                this.attachmentCodeEditor.setValue("");
                $("#editor_attachment .CodeMirror").css("background","none repeat scroll 0 0 #FFFFFF");
                this.attachmentCodeEditor.setOption("mode",this.editorMode);
                this.attachmentCodeEditor.setValue(this.attachment);        
            }            
            this.attachmentCodeEditor.focus();
            this.notifySuccess("Attachment Loaded.");
            break;
        default:
            var _html = '<div class="centered span6 align_center m-t-80">';
            _html += '<h3>No Content Loaded</h3>';
            _html += '</div>';
            $("#editor_file").empty();
            $("#editor_file").html(_html);
            $("#editor_attachment").empty();
            $("#editor_attachment").html(_html);
            //$(".currently_editing").text("No File Selected");
            $("#ide_status_message").text("");
            this.fileCodeEditor = null;
            this.currentview = "empty";
            this.attachment = null;
            this.attachmentCodeEditor = null;
            this.fileCodeEditor = null;
            $('#ide_tab_ctrl a[href="#filecontent_tab"]').tab("show");
            break;
    }
};

Editor.prototype.notifySuccess = function(message){
    $("#ide_status_message").hide();
    $("#ide_notification p").text(message);
    $("#ide_notification").attr("class","success");
    $("#ide_notification").show();
    setTimeout(function(){
        $("#ide_notification").fadeOut(2000, 0.0, function(){
            $("#ide_status_message").show();
        });
    }, 7000);
};

Editor.prototype.notifyError = function(message){
    $("#ide_status_message").hide();
    $("#ide_notification p").text(message);
    $("#ide_notification").attr("class","error");
    $("#ide_notification").show();
    setTimeout(function(){
        $("#ide_notification").fadeOut(2000, 0.0, function(){
            $("#ide_status_message").show();
        });
    }, 7000);
};


function SidePanel(options){
    this.openfiles = [];
    this.maxfiles = options.maxFiles || 10;    
}

SidePanel.prototype.closeFile = function(file){
    var _delIndex = -1;
    _.each(this.openfiles, function(item, index){
        var dbmatch = item.postdata.database == file.postdata.database;
        var filematch = item.postdata.filepath == file.postdata.filepath;                
        if(dbmatch && filematch){
            _delIndex = index;
        }
    });
    
    if(_delIndex > -1){
        this.openfiles.splice(_delIndex,1);
        file = null;
        this.showTab("filelist");
    }
};

SidePanel.prototype.render = function(){
    // setup tab control
    $("#side_panel_nav a:last").text("Opened Files (" + this.openfiles.length + ")");            
    $("#side_panel_nav a:last").bind("click", {view: this}, function(event){
        event.preventDefault();
        event.data.view.showTab("filelist");
    });
    
    $("#side_panel_nav a:first").bind("click", {view: this}, function(event){
        event.preventDefault();
        event.data.view.showTab("openfile");
    });
    
    var currentview = this;
    // setup form filepath autocomplete
    $("#frm_loadfile input[name=filepath]").typeahead({
        source: function(query, process){
            var _data = {
                username:$("#frm_loadfile input[name=username]").val(),
                password:$("#frm_loadfile input[name=password]").val(),
                database:$("#frm_loadfile input[name=database]").val(),
                query:query
            };
            
            if(_data.username.length > 0 &&
               _data.password.length > 0 &&
               _data.database.length > 0){
                // check active connections
                var _active_conn_key = _data.username + ":" + _data.database;
                if(_active_conn_key in ActiveConnections){
                    var connection = ActiveConnections[_active_conn_key]
                }
                else{
                    var connection = new BytengineConnector({username:_data.username,
                                                             password: _data.password,
                                                             database: _data.database})
                    try{
                        connection.connect();
                        ActiveConnections[_active_conn_key] = connection;
                    }
                    catch(error){
                        currentview.notifyError(error);
                    }
                }
                
                var _index1 = query.lastIndexOf("/");
                if(_index1 > 0){
                    var path = query.substring(0,_index1);
                }
                else if(_index1 == 0){
                    var path = "/";
                }
                else{
                    process([]);
                }
                
                var cmd2 = {
                    command:"ls '" + path + "'",
                    onSuccess: function(response){
                        var _dirs = response.data.dirs.sort();
                        var _files = response.data.files.sort();
                        var _afiles = response.data.afiles.sort();
                        var _final = [];
                        if(path == "/"){ path = ""; }
                        _.each(_dirs, function(item){
                            _final.push(path + "/" + item);
                        });
                        _.each(_files, function(item){
                            _final.push(path + "/" + item);
                        });
                        _.each(_afiles, function(item){
                            _final.push(path + "/" + item);
                        });                                        
                        process(_final);
                    },
                    onError: function(error){
                        process([]);
                    }
                };
                connection.command(cmd2);
            }
            else{
                process([]);
            } 
        }
    });
    
    // load file
    $('form').bind("submit", {view: this}, function(event){
        event.preventDefault();
        if(event.data.view.openfiles.length >= event.data.view.maxfiles){
            return;
        }
        var _filepath = $("#frm_loadfile input[name=filepath]").val();
        var _database = $("#frm_loadfile input[name=database]").val();
        var _username = $("#frm_loadfile input[name=username]").val();
        var _password = $("#frm_loadfile input[name=password]").val();
        
        var postdata = {
            database:_database,
            username:_username,
            password:_password,
            filepath:_filepath
        };
        
        // check if file already open
        var isopen = false;
        _.each(event.data.view.openfiles, function(item){
            var dbmatch = item.postdata.database == postdata.database;
            var filematch = item.postdata.filepath == postdata.filepath;                
            if(dbmatch && filematch){
                isopen = true;
            }
        });
        
        if(isopen){
            event.data.view.notifyError("File already open for editing.");
            return;
        }
        else{
            event.data.view.loadFile(postdata);
        }
    });
};

SidePanel.prototype.loadFile = function(postdata){
    $.ajax({
        url: "/ui/ide/load/file",
        type: "POST",
        data: postdata,
        dataType: "text",
        context: this,
        success: function(response, textStatus, jqXHR){
            _mode = jqXHR.getResponseHeader('Bytengine-IDE-Mode');
            $("#frm_loadfile input[name=filepath]").val("");
            if(postdata.filepath.length > 20){
                var path_short = postdata.filepath.substr(0,20) + "...";
            }
            else{
                var path_short = postdata.filepath;
            }
            var _file = {
                path_long:postdata.filepath,
                path_short:path_short,
                data:response,
                postdata:postdata
            };
            this.openfiles.push(_file);
            this.showTab("filelist");
            // trigger event
            $(this).trigger("ideEditSelectedFile",[_file]);
        },
        error: function(jqXHR, textStatus, errorThrown){
            if(jqXHR.responseText){
                this.notifyError(jqXHR.responseText);
            }
            else{
                this.notifyError(errorThrown);
            }                    
        }
    });
};

SidePanel.prototype.reloadFile = function(options){
    $.ajax({
        url: "/ui/ide/load/file",
        type: "POST",
        data: options.file.postdata,
        dataType: "text",
        context: this,
        success: function(response, textStatus, jqXHR){
            options.file.data = response;
            options.onSuccess(options.file);
        },
        error: function(jqXHR, textStatus, errorThrown){
            if(jqXHR.responseText){
                options.onError(jqXHR.responseText);
            }
            else{
                options.onError(errorThrown);
            }                    
        }
    });
};

SidePanel.prototype.loadAttachment = function(options){
    $.ajax({
        url: "/ui/ide/load/attachment",
        type: "POST",
        data: options.file.postdata,
        dataType: "text",
        context: this,
        success: function(response, textStatus, jqXHR){
            _mode = jqXHR.getResponseHeader('Bytengine-IDE-Mode');
            // trigger event
            $(this).trigger("ideEditSelectedAttachment",[_mode, response]);
        },
        error: function(jqXHR, textStatus, errorThrown){
            if(jqXHR.responseText){
                options.onError(jqXHR.responseText);
            }
            else{
                options.onError(errorThrown);
            }                    
        }
    });
};

SidePanel.prototype.showTab = function(name){
    switch(name){
        case "openfile":
            $("#side_panel_nav a:first").tab("show");
            break;
        case "filelist":
            $("#openedfiles_list").empty();
            var template = _.template($("#tmpl_openfiles_links").html());
            $("#openedfiles_list").html(template({files:this.openfiles}));
            $(".show_file_in_editor").bind("click", {view: this}, function(event){
                event.preventDefault();
                var _index = parseInt($(this).attr("index"));
                var _file = event.data.view.openfiles[_index];
                $(event.data.view).trigger("ideEditSelectedFile",[_file]);
            });
            $("#side_panel_nav a:last").text("Opened Files (" + this.openfiles.length + ")");
            $("#side_panel_nav a:last").tab("show");
            break;
        default:
            break;
    }
};

SidePanel.prototype.notifyError = function(message){
    $("#notification_sidepanel").attr("class","error");
    $("#notification_sidepanel p").text(message);
    $("#notification_sidepanel").show();
    setTimeout(function(){
        $("#notification_sidepanel").fadeOut(2000, 0.0);
    }, 7000);
};

SidePanel.prototype.notifySuccess = function(message){
$("#notification_sidepanel").attr("class","success");
    $("#notification_sidepanel p").text(message);
    $("#notification_sidepanel").show();
    setTimeout(function(){
        $("#notification_sidepanel").fadeOut(2000, 0.0);
    }, 7000);
};

// on document ready
$(function(){
    var sidepanel = new SidePanel({});
    sidepanel.render();
    
    var editor = new Editor({loaderControl: sidepanel});
    editor.refresh();
});