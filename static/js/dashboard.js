$(function(){
	// checkbox select all or cancel all
	$("input[name='checkall']").click(function(){
		var checkbox = $("input[name='cc']");
		if(this.checked){
			checkbox.prop("checked", true);  
		}else{
			checkbox.prop("checked", false);
		}
	});

	$("input[name='confirm_task']").click(function(){
		var result = gether_table();
		$("#hidTD").val(JSON.stringify(result));
		$("#form").submit();
	});

	$("input[name='submit_checkbox']").click(function(){
		var result = gether_checkbox();
		$("#hidTD").val(JSON.stringify(result));
		$("#form").submit();
	});

})

// function update_waitlist(){
	  // record all checkbox val
		// var all = [];
		// $("input:checkbox").each(function() {
		// 		all.push($(this).attr("value"));
		// });

		// addup checked values
// 		var che = [];
// 		$("input[name='cc']:checked").each(function() {
// 				che.push({"11":$(this).val()});
// 		});
// 		alert(che)
// 		// post result
// 		$.post("/dashboard/waitlist",{wailist:che});

// 		//remove checked
// 		$("input:checkbox").each(function() {
// 			$(this).prop("checked", false);
// 		});
// 		alert("added to waitlist");
// }

function remove_from_waitlist(obj){
	var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");
	$.post("/dashboard/waitlist", {delete:$(tds[0]).html()});
	tr.parentNode.removeChild(tr);
}
function process_task(obj){
	var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");
	$.post("/deploy/list/work", {"method":obj.name,"id":$(tds[0]).html()});
}
function trasfer_data(obj){
	var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");
	$.get("/deploy/assignment", {"stgs":$(tds[4]).html()});
}
function withdraw(obj){
		var tr = obj.parentNode.parentNode;
		var tds = $(tr).find("td");
		document.getElementById(obj.name).innerHTML="withdrawn";
		document.getElementById("link"+obj.name).innerHTML="N/A";
		$.get("/dashboard/task_sheet/"+obj.name);
    }

	
function gether_table(){
	var tr = $("#table tr");
	var result = [];
	
	for (var i=1; i<tr.length; i++){
		var tds = $(tr[i]).find("td");
		if (tds.length>0){
			result.push($(tds[1]).html());
		}
	}
	return result
}

function gether_checkbox(){
	var result = [];
	$("input[name='cc']").each(function(){
		if(this.checked){
			var row = $(this).parent("td").parent("tr");//获取当前行
			var tds = $(row).find("td");
			result.push({"name":$(tds[1]).html(), "id":$(this).val()});
		}
		
	})
	return result
}
function check_name(){
    var originName = $.trim($("input[name='name']").val());
    if(originName){
        $.ajax({
            url:"/dy",
            type: "GET",
            dataType:"json",
            data: {"checkName":originName},
            success:function(response){
                if(response){
                    $("input[name='name']").css({"color":'red'});
                    document.getElementById("nametip").className ="prompt_alert";
                    $("#nametip").html('该策略名已经被使用');
                    $("#submitbutton").attr({"disabled":"disabled"});
                }else{
                    $("input[name='name']").css({"color":'green'});
                    document.getElementById("nametip").className ="prompt";
                    $("#nametip").html('该策略名可用');
                    document.getElementById("submitbutton").disabled=false;
                }
            },
        });
    }
    else{
        $("#nametip").html('');
    }
}

function check_user(){
    var originName = $.trim($("input[name='name']").val());
    if(originName){
        $.ajax({
            url:"/dy",
            type: "GET",
            dataType:"json",
            data: {"checkUser":originName},
            success:function(response){
                if(response){
                    $("input[name='name']").css({"color":'red'});
                    $("#nametip").class('alert');
                    $("#nametip").html('该用户名已经被使用');
                }else{
                    $("input[name='name']").css({"color":'green'});
                    $("#nametip").html('该用户名可用');
                }
            },
        });
    }
    else{
        $("#nametip").html('');
    }
}
function getAccount(_id) {
    $.ajax({
        url:"/dy",
        type: "GET",
        dataType:"json",
        data: {"getAccount":"accounts"},
        success:function(response){
            if(response){
                var parent = document.getElementById(_id);
                clearOption(parent);
                var opt=document.createElement("option");
                opt.text = " choose a exchage";
                opt.value = " ";
                parent.options.add(opt);
                var res = Object.keys(response);
                addOption(parent, res);
            }else{
                $("#actip").html('账户连接失败');
            }
        },
    });
}
function updateAccount(obj){
    var _id = obj.parentNode.firstElementChild.id;
    getAccount(_id);
}
function changeOpt(obj){
    $.ajax({
        url:"/dy",
        type: "GET",
        dataType:"json",
        data: {"getAccount":"accounts"},
        success:function(response){
            if(response){
                var _id = obj.parentNode.id;
                var p_value = obj.value;
                var child = document.getElementById("child"+_id);
                clearOption(child);
                addOption(child,response[p_value][0]);

                var child2 = document.getElementById("child2"+_id);
                clearOption(child2);
                addOption(child2,response[p_value][1]);
            }else{
                $("#actip").html('账户连接失败');
            }
        },
    });
}

function clearOption(obj){
    var c_length = obj.options.length;
    if(c_length>0){
        for(var i=0;i<c_length;i++){
            obj.options.remove(0);
        }
    }
}

function addOption(obj, content){
    for (_id in content){
        var opt=document.createElement("option");
        opt.text = content[_id];
        opt.value = content[_id];
        obj.options.add(opt);
    }
}

function addSymbolRow(obj){
    var add_item = obj.parentNode;
    var nodeFather = obj.parentNode.parentNode;
    var node_clone = add_item.cloneNode(true); 
    node_clone.id = add_item.id+1
    node_clone.children[0].id = add_item.children[0].id+1;
    node_clone.children[1].id = add_item.children[1].id+1;
    node_clone.children[2].id = add_item.children[2].id+1;
    nodeFather.appendChild(node_clone); 
    getAccount(node_clone.children[0].id);
}

function removeSymbolRow(obj){
    var add_item = obj.parentNode;
    var nodeFather = obj.parentNode.parentNode;
    nodeFather.removeChild(add_item); 
    
}

function checkform(){
    if($("#nametip").html()=='该策略名已经被使用'){
        alert('该策略名已经被使用');
        return;
    };
}