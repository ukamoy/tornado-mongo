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
    
    $(".navbar-nav").find("li").each(function () {
        var a = $(this).find("a:first")[0];
        if ($(a).attr("href") === location.pathname) {
            $(this).addClass("active");
        } else {
            $(this).removeClass("active");
        }
    });
})
function GoBackward(){
    window.history.back();
    }
function check_submission(){
    if(window.confirm("Are you sure?")){
        return true;
    }else{
        return false;
    }
}
function remove_row(obj){
	var tr = obj.parentNode.parentNode;
    var tds = $(tr).find("td");
	$.post("/ding?delete="+obj.name);
	tr.parentNode.removeChild(tr);
}
function process_task(obj){
	var tr = obj.parentNode.parentNode;
    var tds = $(tr).find("td");
    var _id = $(tds[0]).html();
    document.getElementById(_id).innerHTML = obj.name;
	document.getElementById("link"+_id).innerHTML="N/A";
	$.post("/deploy/list/work", {"method":obj.name,"id":_id});
}
function trasfer_data(obj){
	var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");
	$.get("/deploy/assignment", {"stgs":$(tds[4]).html()});
}

function submit_task(obj){
    var result = gether_checkbox();
    if(result.length==0){
        alert("please pick strategy");
    }else{
        $.ajax({
            url:"/dashboard/tasks/add",
            type: "POST",
            dataType:"json",
            data: result,
            beforeSend:task_processing,
            error:null,
            complete:task_complete,
            success:function(response){
                if(response){
                    window.location.href="/dashboard/tasks/"+response;
                }else{
                    alert("create task failed");
                }
            },
        });
    };
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
			result.push({"name":$(this).val(),"id":$(tds[2]).html()});
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
            success:check_name_success
        });
    }
    else{
        $("#nametip").html('');
    }
}
function check_ding(){
    var originName = $.trim($("input[name='ding_name']").val());
    if(originName){
        $.ajax({
            url:"/dy",
            type: "GET",
            dataType:"json",
            data: {"checkDing":originName},
            success:check_name_success
        });
    }
    else{
        $("#nametip").html('名称必填');
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
            success:check_name_success
        });
    }
    else{
        $("#nametip").html('');
    }
}
function check_name_success(response){
    if(response){
        $("input[name='name']").css({"color":'red'});
        document.getElementById("nametip").className ="prompt_alert";
        $("#nametip").html('该名称已经被使用');
        $("#submitbutton").attr({"disabled":"disabled"});
    }else{
        $("input[name='name']").css({"color":'green'});
        document.getElementById("nametip").className ="prompt";
        $("#nametip").html('该名称可用');
        document.getElementById("submitbutton").disabled=false;
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
                opt.text = " choose exchage";
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

function old_operator(obj) {
    var s = obj.name.split("-");
    var name = s[1];
    var method = s[0];
    var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");

    $.ajax({
        url:"/old_operator",
        type: "POST",
        dataType:"json",
        data: {"name":name,"method":method},
        beforeSend:task_processing,
        complete:task_complete,
        error:null,
        success:function(response){
            if(response){
                if (method=="halt"){
                    $(tds[1]).html("idle");
                    alert(name+" halted");};
            }else{
                alert(name+" "+method+" operation failed");
            }
        },
    });
}
function operator(obj) {
    var s = obj.name.split("-");
    var method = s[0];
    var name = s[1];
    var task_id = s[2];
    
    var select = document.getElementById("server-"+name);
    var index = select.selectedIndex;
    var server = select.options[index].text;
    if(server=="idle" & method!="archive"){return alert("please choose server");};
    if(method=="halt"){
        var r = check_submission();
        if(r==false){
            return;
        }
    }

    $.ajax({
        url:"/operator",
        type: "POST",
        dataType:"json",
        data: {"method":method, "name":name, "task_id":task_id,"server":server},
        beforeSend:task_processing,
        complete:task_complete,
        error:null,
        success:function(response){
            if(response){
                if ("error" in response){
                    return alert(response["error"]);
                }else{
                    var result = response["result"];
                    if(result){
                        if (method=="halt"){
                            select.value = "idle";
                            $(obj).attr("disabled","disabled");
                            $(obj).css("pointer-events","none");
                            var t = obj.name.split("-");
                            var new_obj = document.getElementsByName("launch-"+t[1]+"-"+t[2]);
                            $(new_obj).attr("disabled",false);
                            $(new_obj).css("pointer-events","auto");
                            alert(name+" halted");

                        }else if(method=="launch"){
                            $(obj).attr("disabled","disabled");
                            $(obj).css("pointer-events","none");
                            var t = obj.name.split("-");
                            var new_obj = document.getElementsByName("halt-"+t[1]+"-"+t[2]);
                            $(new_obj).attr("disabled",false);
                            $(new_obj).css("pointer-events","auto");
                            alert(name+"  launched");
                        }else if(method=="archive"){
                            window.open("/static/Strategy/"+task_id+"/"+response["result"])
                            };
                    }else{
                        alert(name+" "+method+" operation failed");
                    }
                }
            }else{
                alert(name+" "+method+" operation failed");
            }
        },
    });
}

function task_processing(){
    var zhezhao=document.getElementById("zhezhao"); 
    var msg=document.getElementById("msg"); 
    zhezhao.style.display="block"; 
    msg.style.display="block"; 
}
function task_complete(){
    var zhezhao=document.getElementById("zhezhao"); 
    var msg=document.getElementById("msg"); 
    zhezhao.style.display="none"; 
    msg.style.display="none"; 
}

function error(XMLHttpRequest, textStatus, errorThrown){
    // 通常情况下textStatus和errorThown只有其中一个有值 
    $("#showResult").append("<div>请求出错啦！</div>");
}
function beforeSend(XMLHttpRequest){
    $("#showResult").append("<div><img src='../static/loading.gif' />Processing..<div>");
}
function complete(XMLHttpRequest, textStatus){
    $("#showResult").remove();
}
function render(instrument,pnl,qty){
    Highcharts.chart(instrument, {
        chart: {
                zoomType: 'x'
        },
        title: {
                text: 'PnL Chart Over Time'
        },
        subtitle: {
                text: document.ontouchstart === undefined ?
                    'Click and drag in the plot area to zoom in' : 'Pinch the chart to zoom in'
        },
        xAxis: [{
            type: 'datetime'
        }],
        yAxis: [{ // 主Y轴
            labels: {
                format: '{value}',
                style: {
                    color: '#89A54E',
                    fontSize: '12px'
                }
            },
            title: {
                text: 'PNL',
                style: {
                    color: '#89A54E',
                    fontSize: '12px'
                }
            }
        }, { // 次Y轴
            title: {
                text: 'VOLUME',
                style: {
                    color: '#4572A7'
                }
            },
            labels: {
                format: '{value}',
                style: {
                    color: '#4572A7'
                }
            },
            opposite: true
        }],
        tooltip: {
            shared: true
        },
        legend: {
            //enabled: false
            legend: {
                layout: 'vertical',
                align: 'left',
                x: 120,
                verticalAlign: 'top',
                y: 100,
                floating: true,
                backgroundColor: (Highcharts.theme && Highcharts.theme.legendBackgroundColor) || '#FFFFFF'
            },
        },
        series: [{
            name: 'VOLUME',
            color: '#4572A7',
            type: 'column',
            yAxis: 1,
            data: qty,
            tooltip: {
                valueSuffix: ' '
            }

        }, {
            name: 'PNL',
            color: '#89A54E',
            type: 'spline',
            data: pnl,
            tooltip: {
                valueSuffix: ' '
            }
        }]
    })
 };
 
//查找表格的<th>元素，让它们可单击
function makeSortable(table) {
    var headers=table.getElementsByTagName("th");
    for(var i=0;i<headers.length;i++){
        (function(n){
            var flag=false;
            headers[n].onclick=function(){
                // sortrows(table,n);
                var tbody=table.tBodies[0];//第一个<tbody>
                var rows=tbody.getElementsByTagName("tr");//tbody中的所有行
                rows=Array.prototype.slice.call(rows,0);//真实数组中的快照

                //基于第n个<td>元素的值对行排序
                rows.sort(function(row1,row2){
                    var cell1=row1.getElementsByTagName("td")[n];//获得第n个单元格
                    var cell2=row2.getElementsByTagName("td")[n];
                    var val1=cell1.textContent||cell1.innerText;//获得文本内容
                    var val2=cell2.textContent||cell2.innerText;

                    if(val1<val2){
                        return -1;
                    }else if(val1>val2){
                        return 1;
                    }else{
                        return 0;
                    }
                });
                if(flag){
                    rows.reverse();
                }
                //在tbody中按它们的顺序把行添加到最后
                //这将自动把它们从当前位置移走，故没必要预先删除它们
                //如果<tbody>还包含了除了<tr>的任何其他元素，这些节点将会悬浮到顶部位置
                for(var i=0;i<rows.length;i++){
                    tbody.appendChild(rows[i]);
                }

                flag=!flag;
            }
        }(i));
    }
}

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
//        var link=location.href.substring(location.href.indexOf("?")+1);
//       var ding_name = link.split("=")[1];
//        $.post("/ding?delete="+ding_name);
// }