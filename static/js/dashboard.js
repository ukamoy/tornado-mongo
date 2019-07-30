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
window.onload=function(){
    var table=document.getElementsByTagName("table")[0];
    makeSortable(table);
}
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

function create_instance(){
    var result = gether_checkbox();
    if(result.length==0){
        alert("please pick strategy");
    }else{
        var mark=[];
        for(var stg in result){
            if(result[stg]["id"] != "idle"){
                mark.push(result[stg]['name']);
            }
        }
        if(mark.length==0){
            $.ajax({
                url:"/dashboard/tasks/add",
                type: "POST",
                dataType:"json",
                data: result,
                beforeSend:task_processing,
                complete:task_complete,
                success:function(response){
                    if(response){
                        window.location.href="/dashboard/tasks/instance";
                    }else{
                        alert("create instance failed");
                    }
                },
            });
        }else{
            alert(mark+": strategy already in running");
        }
    };
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
function check_pwd(){
    var originName = $.trim($("input[name='pwd']").val());
    if(originName){
        $.ajax({
            url:"/dy",
            type: "GET",
            dataType:"json",
            data: {"checkPwd":originName},
            success:function(response){
                if(response){
                    document.getElementById("pwd_tip").className ="prompt";
                    $("#pwd_tip").html('passed');
                    document.getElementById("submitbutton").disabled=false;
                }else{
                    document.getElementById("pwd_tip").className ="prompt_alert";
                    $("#pwd_tip").html('wrong pwd');
                    $("#submitbutton").attr({"disabled":"disabled"});
                }
            }
        });
    }
    else{
        $("#pwd_tip").html('');
    }
}
function check_confirm_pwd(){
    var new_pwd = $.trim($("input[name='new_pwd']").val());
    var confirm_pwd = $.trim($("input[name='confirm_pwd']").val());
    if(new_pwd.length>7){
        if(new_pwd==confirm_pwd){
            $.ajax({
                url:"/reset",
                type: "POST",
                dataType:"json",
                data: {"new_pwd":new_pwd},
                success:function(response){
                    if(response){
                        document.getElementById("confirm_pwd_tip").className ="prompt";
                        $("#confirm_pwd_tip").html('update success');
                    }else{
                        document.getElementById("confirm_pwd_tip").className ="prompt_alert";
                        $("#confirm_pwd_tip").html('update failed');
                    }
                },
            });
            
        }else{
            document.getElementById("confirm_pwd_tip").className ="prompt_alert";
            $("#confirm_pwd_tip").html('not same');
        }
    }else{
        document.getElementById("confirm_pwd_tip").className ="prompt_alert";
            $("#confirm_pwd_tip").html('password should at least 8 digits');
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

function operate_multi(obj){
    var r = check_submission();
        if(r==false){
            return;
        }
    var method = obj.name.split("_")[0];
    var result = gether_checkbox();
    var msg = [];
    if(result.length==0){
        alert("please pick strategy");
    }else{
        for(item in result){
            res = result[item]["name"].split("-")
            name=res[0];
            task_id=res[1];
            server=res[2];
        
            $.ajax({
                url:"/operator",
                type: "POST",
                dataType:"json",
                data: {"method":method, "name":name, "task_id":task_id,"server":server},
                beforeSend:task_processing,
                complete:task_complete,
                error:null,
                async:false,
                success:function(response){
                    if(response){
                        if ("error" in response){
                            return alert(response["error"]);
                        }else{
                            var result = response["result"];
                            if(result){
                                if (method=="halt"){
                                    var button = document.getElementsByName("halt-"+name+"-"+task_id);
                                    $(button).attr("disabled","disabled");
                                    $(button).css("pointer-events","none");
                                    var new_obj = document.getElementsByName("launch-"+name+"-"+task_id);
                                    $(new_obj).attr("disabled",false);
                                    $(new_obj).css("pointer-events","auto");
                                    msg.push(name);
        
                                }else if(method=="delete"){
                                    var button = document.getElementsByName("delete-"+name+"-"+task_id);
                                    var tr = $(button)[0].parentNode.parentNode;
                                    tr.parentNode.removeChild(tr);
                                    // alert("Moved to Archiver");
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
        };
        if(method=="halt"){alert(msg+", halted");};
    }
}

function operator(obj) {
    var s = obj.name.split("-");
    var method = s[0];
    var name = s[1];
    var task_id = s[2];
    
    var select = document.getElementById("server-"+name);
    var index = select.selectedIndex;
    var server = select.options[index].text;
    if(server=="idle" & method!="delete"){return alert("please choose server");};
    if(method =="halt" | method=="delete"){
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
                        }else if(method=="delete"){
                            var tr = obj.parentNode.parentNode;
                            tr.parentNode.removeChild(tr);
                            alert("Moved to Archiver");
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
    var overlay=document.getElementById("overlay"); 
    var msg=document.getElementById("msg"); 
    overlay.style.display="block"; 
    msg.style.display="block"; 
}
function task_complete(){
    var overlay=document.getElementById("overlay"); 
    var msg=document.getElementById("msg"); 
    overlay.style.display="none"; 
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
    $("#loading").append("<div id='showResult'></div>");
}
function clear_pos(obj){
    var r = check_submission();
        if(r==false){
            return;
        }
    var name = obj.name;
    $.ajax({
        url:"/dy",
        type: "GET",
        dataType:"json",
        data: {"checkPos":name},
        beforeSend:task_processing,
        complete:task_complete,
        error:null,
        success:function(response){
            if(JSON.stringify(response)=="{}"){
                return alert("no position to clear!");
            }else{
                for(var sym in response){
                    $.post("/operator/clear_pos",{"symbol":sym,"qty":response[sym],"strategy":name})
                }
                alert("command sent");
            }
        }
    });
}

function account_value(hist,coin,){
    return {
        tooltip: {
            trigger: 'axis',
            position: function (pt) {
                return [pt[0], '10%'];
            }
        },
        title: {
            left: 'center',
            text: 'Account-'+coin,
        },
        toolbox: {
            show:false,
            feature: {
                dataZoom: {
                    yAxisIndex: 'none'
                },
                restore: {},
                saveAsImage: {},
                mark:{
                    title:{
                        mark:"MARK",
                        download:"DOWNLOAD"
                }}
            }
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
        },
        yAxis: {
            type: 'value',
            boundaryGap: [0, '100%'],
            scale:true,
        },
        dataZoom: [{
            type: 'inside',
            start: 0,
            end: 100
        }, {
            start: 90,
            end: 100,
            handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
            handleSize: '50%',
            handleStyle: {
                color: '#fff',
                shadowBlur: 3,
                shadowColor: 'rgba(0, 0, 0, 0.6)',
                shadowOffsetX: 2,
                shadowOffsetY: 2
            }
        }],
        series: [
            {
                name:coin,
                type:'line',
                color:'#00BFFF',
                smooth:true,
                markLine: {
                    data: [
                        {type: 'average', name: '平均值'}
                    ]
                },
                markPoint: {
                    symbol:"pin",
                    data: [
                        {type: 'max', name: '最大值'},
                        {type: 'min', name: '最小值'}
                    ],
                    label:{
                        formatter: function(value) {
                           return value.value.toFixed(2);
                        }
                      },
                    precision: 3,
                },
                data: hist
            }
        ]
    };
    ;
    
}


function running_hist(hist){
    var dom = document.getElementById("running_history");
    var myChart = echarts.init(dom);

    option = {
        tooltip: {
            trigger: 'axis',
            position: function (pt) {
                return [pt[0], '10%'];
            }
        },
        title: {
            left: 'center',
            text: 'Strategy Operation(0 : halt, 1 : launch)',
        },
        toolbox: {
            show:false,
            feature: {
                dataZoom: {
                    yAxisIndex: 'none'
                },
                restore: {},
                saveAsImage: {},
                mark:{
                    title:{
                        mark:"MARK",
                        download:"DOWNLOAD"
                }}
            }
        },
        xAxis: {
            type: 'time',
            boundaryGap: false,
        },
        yAxis: {
            type: 'value',
            boundaryGap: [0, '100%']
        },
        dataZoom: [{
            type: 'inside',
            start: 0,
            end: 100
        }, {
            start: 90,
            end: 100,
            handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
            handleSize: '50%',
            handleStyle: {
                color: '#fff',
                shadowBlur: 3,
                shadowColor: 'rgba(0, 0, 0, 0.6)',
                shadowOffsetX: 2,
                shadowOffsetY: 2
            }
        }],
        series: [
            {
                name:'operation',
                type:'line',
                smooth:false,
                symbol: 'none',
                sampling: 'average',
                itemStyle: {
                    color: 'rgb(255, 70, 131)'
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                        offset: 0,
                        color: 'rgb(255, 158, 68)'
                    }, {
                        offset: 1,
                        color: 'rgb(255, 70, 131)'
                    }])
                },
                data: hist
            }
        ]
    };
    ;
    if (option && typeof option === "object") {
        myChart.setOption(option, true);
    }
}
function performance(instrument,pnl,qty){
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
                    color: '#00BFFF',
                    fontSize: '12px'
                }
            },
            title: {
                text: 'PNL',
                style: {
                    color: '#00BFFF',
                    fontSize: '12px'
                }
            }
        }, { // 次Y轴
            title: {
                text: 'VOLUME',
                style: {
                    color: '#C9C9C9'
                }
            },
            labels: {
                format: '{value}',
                style: {
                    color: '#C9C9C9'
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
            color: '#C9C9C9',
            type: 'column',
            yAxis: 1,
            data: qty,
            tooltip: {
                valueSuffix: ' '
            }

        }, {
            name: 'PNL',
            color: '#00BFFF',
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
    // $(headers).append("&nbsp;<i class='glyphicon glyphicon-sort'></i>");
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
function check_pos(pos){
    var form = document.getElementById("strategy_form")
    if(pos=="0"){
        //alert("ok");
        form.submit();
    }else{
        return alert(pos);
    }
}
function delete_stg(obj){
    var r = check_submission();
        if(r==false){
            return;
        }
    var name = obj.name;
    $.get("/dy",{"deleteStrategy":name});
    window.location.href="/";
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