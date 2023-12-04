
    //
    // 在指定的div里使用ajax载入一个页面，在载入过程显示“正在载入...”的动画
    //
    // $target      jQuery对象
    // targetUrl    要载入的目标地址
    //
    // 示例： load($('#main-content'), 'dashboard')
    //
    function load($target, targetUrl, cache, $progressContainer) {
      $('body').modalmanager('loading');
      var $progressBar = $('#id-progressbar');
      if (!$progressBar || !$progressBar.length) {
        var height = $(window).height();
        var width = $(window).width();
        $progressContainer = $progressContainer || $target;
        $progressContainer.append(
            '<div id="id-progressbar" style="position:absolute; left:' + width / 2 + 'px; top:' + height / 2 + 'px; z-index:1; display:none;" class="well well-large well-transparent lead">\
              <i class="fa fa-spinner fa-spin fa-2x pull-left"></i> 正在载入，请稍候...\
            </div>'
        );
        $progressBar.fadeIn("slow");
      }
      var cache = cache || false;
      $.ajax({
        url: targetUrl,
        type: "GET",
        cache: cache,
        error: function(jqXHR, textStatus, errorThrown) {
          $target.showServerResponseError(jqXHR.responseText, jqXHR, targetUrl);
        }
      }).done(function(html){
        $target.html(html);
        $target.trigger('loadingDone');
      }).always(function(){
        $('body').modalmanager('loading');
        //XXX: MUST call 'removeLoading' to make dismiss works on chrome.
        $('body').modalmanager('removeLoading');

        if ($progressBar) {
          $progressBar.fadeOut();
        }
      });
    }

    // handle
    // <a href="#" data-url="realm" data-target="main-content">Intro</a>
    //
    function bindClickLinkAction() {
      $(document).on('click', 'a[data-url]', function (e) {
        var targetUrl = $(this).data('url');
        var targetDiv = $(this).data('target');
        if (targetUrl) {
          if (!targetDiv) {
            targetDiv = 'main-content';
          }
          var shouldCheckAccess = $(this).data('check_access');
          if (shouldCheckAccess) {
            $.ajax({
              url: targetUrl,
              type: "GET",
              data: "check_access",
              success: function (response) {
                if (response['ret'] == 0) {
                  window.location.hash = targetUrl + "#" + targetDiv;
                } else {
                  bootboxAlert("出错了", response['errmsg']);
                }
              },
              error: function () {
                bootboxAlert("出错了", "错误:访问服务器错误.");
              }
            });
          } else {
            var hash = targetUrl + "#" + targetDiv
            if ($(this).data('cache')) {
               hash = hash + "#cache";
            }
            //XXX: change window.location.hash will trigger $(window).hashchange(function (e)
            window.location.hash = hash;
          }
          // avoid the caller to override the window.location.hash with href
          e.preventDefault();
        }
      });
    }

    function showModalPage(url, backdrop) {
        // handle the case that url has contains some parameters.
        url += (url.search(/\/$/) != -1 ? "?" : "&") + "modal=true";
        var $modal_container = $("#id_modal_form_container_master");
        // support modal overlap
        // find the salve modal container if find the master modal is already shown.
        if ($('body').hasClass('modal-open')) {
          $modal_container = $("#id_modal_form_container_slave");
        }
        if (!backdrop) {
          backdrop = '';
        }
        var $modal_dialog = $('.my-modal-dialog', $modal_container);
        $modal_container.modal({
          backdrop: backdrop,
          keyboard: true,
          show: true,
          width: function() {
            return $(window).width() * 0.8;
          },
          modalOverflow: true
        }).on("hide.bs.modal", function(){
          //XXX: should empty the old content to avoid the screen flick during presentation.
          $modal_dialog.empty();
          $modal_container.off("hide.bs.modal");
        });

        $modal_dialog.on("loadingDone", function(){
          //FIXME: CHOSEN will show the "select" with 0 width if the form is presented before page shown
          // a workaround to reload chosen.
          $('form :input[multiple=multiple]:not([type="file"]), form select', $modal_dialog).chosen('destroy').enableChosen();
          $modal_dialog.off("loadingDone");
        });

        load($modal_dialog, url, false, $('#main-content'));
    }

    function bindClickModalLinkAction() {
      $(document).on('click', 'a[data-modalurl]', function (e) {
        var url = $(this).data('modalurl');
        var backdrop = $(this).data('backdrop');
        var shouldCheckAccess = $(this).data('check_access');
        if (shouldCheckAccess) {
          $.ajax({
            url: url,
            type: "GET",
            data: "check_access",
            success: function (response) {
              if (response['ret'] == 0) {
                showModalPage(url, backdrop);
              } else {
                bootboxAlert("出错了", response['errmsg']);
              }
            },
            error: function () {
              bootbox.alert("错误:访问服务器错误.");
            }
          });
        } else {
          showModalPage(url, backdrop);
        }
        e.preventDefault();
      });
    }

    function drawDateTimeFieldWithPicker(orig) {
      var $dateTimeEl = $(origInputElementSel);
      var $dateTimeLabel = $("label[for=" + $dateTimeEl.attr('id') + "]");
      $dateTimeLabel.append('<i class="fa fa-question-circle" style="padding-left:5px;" data-rel="popover" ' +
                          'data-trigger="hover" data-placement="right" ' +
                          'data-content="点击 <i class=\'ace-icon fa fa-calendar blue\'></i> 选择日期，点击 <i class=\'ace-icon fa fa-clock-o blue\'></i> 选择时间" title="" ' +
                          'data-original-title="如何选择任务截止时间"></i>');
      $dateTimeEl.parent().datetimepicker({
        format:'YYYY-MM-DD HH:mm', // align with django datetime field format
        language: 'zh-CN',
        minDate: moment() // do not allow choose the date before today
      });
      $('[data-rel=popover]').popover({container:'body',html:true});
    }

    function drawDateTimeRangePickerField(origInputElementSel, format, startDate, endDate, showTimePicker) {
      $(origInputElementSel).daterangepicker({
        'applyClass' : 'btn-sm btn-success',
        'cancelClass' : 'btn-sm btn-default',
        locale: {
          applyLabel: '确认',
          cancelLabel: '取消',
          fromLabel: '开始时间',
          toLabel:'截止时间'
        },
        timePicker: showTimePicker,
        timeZone: '+08:00',
        timePicker12Hour: false,
        timePickerIncrement: 15,
        format: format,
        language: 'zh-CN',
        minDate: moment(),  // do not allow choose the start date before today
        startDate: startDate,
        endDate: endDate
      });
    }

    function drawTextFieldWithSlider(origInputElementSel, value, min, max, step) {
      var $textInputEl = $(origInputElementSel);
      var $textInputContainer = $textInputEl.parent();
      $textInputContainer.html(''+
                           $textInputContainer.html()+
                          '' +
                          '<div class="space-2"></div>' +
                          '<div class="help-block" id="input-span-slider"></div>');
      $('#input-span-slider', $textInputContainer).slider({
        value:value,
        range: "min",
        min: min,
        max: max,
        step: step,
        slide: function( event, ui ) {
          var testerNum = parseInt(ui.value);
          $(origInputElementSel).val(testerNum);
        }
      });
    }

    // to use the 2 knob functions below, you need to have a knob container like
    //          <div id="id-apk-upload-knob" class="dial-container">
    //            <input type="text" value="0" class="dial hidden">
    //            <div class="dial-label hidden">APK文件上传中...</div>
    //          </div>
    function initKnob(knobContainer, step, width, height, thickness, fgColor) {
      $('.dial', knobContainer).removeClass('hidden').knob({
        'min': 0,
        'max': 100,
        'step': step,
        'readOnly': true,
        'width': width,
        'height': height,
        'fgColor': fgColor,
        'inputColor': fgColor,
        'displayInput':true,
        'thickness': thickness,
        'skin': 'tron',
        'draw' : function () {
          $(this.i).val(this.cv + '%')
        }
      });
      $('.dial', knobContainer).val(0).trigger('change');
      $('.dial-label', knobContainer).removeClass('hidden');
    }

    function updateKonb(knobContainer, prgValue, finishLabel) {
      $('.dial', knobContainer).val(prgValue).trigger('change').delay(0);
      if(prgValue == 100) {
        $('.dial-label', knobContainer).text(finishLabel);
      }
    }

    $(document).ready(function() {
      $.ajaxSetup({cache: false});

      // 注册jquery.validation插件的regex验证方法
      $.validator.addMethod(
        "regex",
        function (value, element, regexp) {
          var re = new RegExp(regexp);
          return this.optional(element) || re.test(value);
        },
        "请输入正确的值!"
      );
      $.validator.setDefaults({
        errorClass: "error",
        errorElement: "label",
        // enable check control "chosen"
        // see http://stackoverflow.com/questions/11232310/how-can-i-use-jquery-validation-with-the-chosen-plugin
        ignore: ":hidden:not(select)",
        errorPlacement: function (error, element) {
          element.parent().append(error);
        }
      });
      ace.data = new ace.data_storage();

      var $sidebar = $('#sidebar');
      var $mainContent = $('#main-content');

      $('a[data-url]', $sidebar).click(function () {
        $('li', $sidebar).removeClass('active');
        $(this).parent().parent().parent().addClass('open active');
        $(this).parent().addClass('active');
      });

      bindClickLinkAction();
      bindClickModalLinkAction();

      $('#id_modal_form_container_master').on("hide.bs.modal", function () {
        //XXX: should empty the old content to avoid the screen flick during presentation.
        $('.my-modal-dialog', $(this)).empty();
      });

      var shouldChooseDefaultMenu = true;
      var activeSubMenuId = ace.data.get("sidebar", "active_submenu");
      if (activeSubMenuId && activeSubMenuId.length !== 0) {
        var $activeMenu = $("#" + activeSubMenuId);
        if ($activeMenu.length !== 0) {
          $('li', $sidebar).removeClass('active');
          $activeMenu.closest("li").trigger("click");
          $activeMenu.trigger("click");
          $mainContent.load($activeMenu.data('url'));
          shouldChooseDefaultMenu = false;
        }
      }
      if (shouldChooseDefaultMenu) {
        // Load default content of main-content.
        $('a', $('li[class=active]', $sidebar)).click();
      }

      // keep the last clicked menu
      $('a.submenu_link, a.has_no_submenu').on("click", function () {
        ace.data.set("sidebar", "active_submenu", this.id);
      });

      $('#id_exit_agent_mode').on('click', function(){
        // jump to "account" list.
        ace.data.set("sidebar", "active_submenu", 'id_menu_2_1');
      });

      $(window).on('hashchange', function () {
        if (location.hash.length > 1) {
          var elements = window.location.hash.split("#");
          var targetUrl = elements[1];
          var $target = $("#" + elements[2]);
          if (!$target.isEmptyObject) {
            var cache = elements[3] === 'cache' ? true : false;
            load($target, targetUrl, cache);
          }
        }
      });

      bootbox.setDefaults({
        locale: "zh_CN"
      });

      $.fn.modal.defaults.spinner = $.fn.modalmanager.defaults.spinner =
        '<div class="loading-spinner well well-large blue" style="width:400px;margin-left: -100px;z-index:9999">' +
           '<i class="fa fa-spinner fa-spin bigger-300 pull-left"></i><h3>正在加载数据，请稍候...</h3>' +
        '</div>';
    });
