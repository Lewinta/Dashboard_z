/* ------------------------------------------------------------------------------------------------------------------ *
 *
 * Template WgBoard - Responsive multipurpose HTML dashboard template
 * Version  1.0
 * Author   Valery Timofeev
 *
 * ------------------------------------------------------------------------------------------------------------------ */

'use strict';

function hex2RGBA(hex, opacity) {

    var r, g, b;

    hex = hex.replace('#', '');

    r = parseInt(hex.substring(0,2), 16);
    g = parseInt(hex.substring(2,4), 16);
    b = parseInt(hex.substring(4,6), 16);

    return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + opacity / 100 + ')';
}

function getRandomNumber(min, max)  {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getRandomDataArray(min, max, count) {

    var data = [];

    for (var i = 0, l = count; i < l; i++) {
        data.push(getRandomNumber(min, max));
    }
    return data;
}

(function($) {

    'use strict';

    /* -------------------------------------------------------------------------------------------------------------- *
     * Variables and Constants
     * -------------------------------------------------------------------------------------------------------------- */

    var THEME_COLORS = {
        PRIMARY:   '#6f21c0',
        SECONDARY: '#00bdd5',
        DARK:      '#333333',
        LIGHT:     '#f7f7f7',
        DEFAULT:   '#00bdd5',
        SUCCESS:   '#13b42b',
        INFO:      '#209ca9',
        WARNING:   '#ec531f',
        DANGER:    '#e31e62'
    };

    var $html = $('html'),
        $body_html = $('body, html'),
        $body = $('body');

    var DAYS_NAMES   = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    var MONTHS_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
                        'October', 'November', 'December'];

    var BREAKPOINTS = {
        LG: 1200,
        MD: 992,
        SM: 768,
        XS: 480
    };

    /* -------------------------------------------------------------------------------------------------------------- *
     * Is Mobile
     * -------------------------------------------------------------------------------------------------------------- */

    var uaTest = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i,
        isMobile = uaTest.test(navigator.userAgent);

    $html.addClass(isMobile ? 'mobile' : 'no-mobile');


    /* -------------------------------------------------------------------------------------------------------------- *
     * Custom Events: Screen Breakpoints
     * -------------------------------------------------------------------------------------------------------------- */

    $(window).on('resize', function() {

        var w = $(this).width();
        var e = 'screen:xs';

        if      (w >= BREAKPOINTS.LG)                       e = 'screen:lg';
        else if (w >= BREAKPOINTS.MD && w < BREAKPOINTS.LG) e = 'screen:md';
        else if (w >= BREAKPOINTS.SM && w < BREAKPOINTS.MD) e = 'screen:sm';

        $(window).trigger(e);
    });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Prevent empty anchors
     * -------------------------------------------------------------------------------------------------------------- */

    $('a[href="#"]').on('click', function(e) {
        e.preventDefault();
    });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Smooth scrolling
     * -------------------------------------------------------------------------------------------------------------- */

    $('.smooth-scroll:not([href="#"])').on('click', function(e) {

        e.preventDefault();

        var $this = $(this),
            target = $this.attr('href');

        if (target === 'undefined') return;

        var $target = $(target);
        if ($target.length === 0) return;

        var offset = $target.offset().top || 0;

        $.scrollWindow(offset - 60);

    });

    $.scrollWindow = function(offset) {
        $body_html.animate({ scrollTop: offset }, 750);
    };


    /* -------------------------------------------------------------------------------------------------------------- *
     * MD-inputs
     * -------------------------------------------------------------------------------------------------------------- */

    $('.md-input').find('.md-control')
        .each(function() {
            var $parent = $(this).parent();
            if ($(this).val() !== '') $parent.addClass('md-completed');
        })
        .on('focus', function() {
            var $parent = $(this).parent();
            $parent.addClass('focus');
        })
        .on('blur', function() {

            var $parent = $(this).parent();
            $parent.removeClass('focus');

            if ($(this).val() !== '') $parent.addClass('md-completed');
            else $parent.removeClass('md-completed');
        })
        .on('input, change', function() {

            var $parent = $(this).parent();

            if ($(this).val() !== '') $parent.addClass('md-completed');
            else $parent.removeClass('md-completed');
        });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Control Feedback
     * -------------------------------------------------------------------------------------------------------------- */

    function setCheckboxLabel() {

        var $this = $(this);
        var id = $this.attr('id');
        var checked = Number(this.checked);

        if (typeof id === 'undefined') return;

        var $label = $('label[for="' + id + '"]');
        if ($label.length === 0) return;

        if (checked === 1) $label.addClass('checkbox-checked');
        else $label.removeClass('checkbox-checked');
    }

    $('.checkbox-feedback')
        .on('change', setCheckboxLabel)
        .each(setCheckboxLabel);


    /* -------------------------------------------------------------------------------------------------------------- *
     * Dropdown animation
     * -------------------------------------------------------------------------------------------------------------- */

    if (!isMobile) {

        $('.dropdown')
            .on('show.bs.dropdown', function() {
                $(this).find('.dropdown-menu').first().stop(true, true).slideDown('fast');
            })
            .on('hide.bs.dropdown', function() {
                $(this).find('.dropdown-menu').first().stop(true, true).slideUp('fast');
            });
    }


    /* -------------------------------------------------------------------------------------------------------------- *
     * Tooltips
     * -------------------------------------------------------------------------------------------------------------- */

    $('[data-toggle=\'tooltip\']').attr('data-animation', true).tooltip({ container: 'body' });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Popovers
     * -------------------------------------------------------------------------------------------------------------- */

    $('[data-toggle="popover"]').popover();


    /* -------------------------------------------------------------------------------------------------------------- *
     * Malihu CustomScrollbar
     * -------------------------------------------------------------------------------------------------------------- */

    var isCustomScrollbarInitialized = false;

    function initCustomScrollbar() {

        if (isCustomScrollbarInitialized) return;

        $('.custom-scrollbar').mCustomScrollbar({
            scrollInertia: 150,
            height       : '100%',
            axis         : 'y'
        });

        isCustomScrollbarInitialized = true;
    }

    function destroyCustomScrollbar() {

        if (!isCustomScrollbarInitialized) return;

        $('.custom-scrollbar').mCustomScrollbar('destroy');

        isCustomScrollbarInitialized = false;
    }

    function toggleCustomScrollbar() {

        var windowWidth = $(window).width();

        if (windowWidth < 768) destroyCustomScrollbar();
        else initCustomScrollbar();

    }

    $(window).on('resize', toggleCustomScrollbar);
    toggleCustomScrollbar();


    /* -------------------------------------------------------------------------------------------------------------- *
     * Circle progress
     * -------------------------------------------------------------------------------------------------------------- */

    // Change defaults
    $.circleProgress.defaults.size      = 130;
    $.circleProgress.defaults.thickness = 2;

    $('.progress-circle').each(function() {

        var $this = $(this);
        var $value = $('<span>');

        var params = {
            value: $this.attr('data-value') || 0,
            fill : THEME_COLORS[($this.attr('data-color') || 'primary').toUpperCase() || 'PRIMARY']
        };

        $this.append($value);
        $this.circleProgress(params);

        $this.on('circle-animation-progress', function(event, progress, stepValue) {
            // $value.html(parseInt((stepValue.toFixed(2).substr(1) * 100).toString(), 10));
            $value.html(roundNumber($this.attr('data-value'), 1)+'%');
        });
    });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Chart.js
     * -------------------------------------------------------------------------------------------------------------- */

    // Doughnut
    Chart.defaults.doughnut.cutoutPercentage       = 75;

    // Global
    Chart.defaults.global.legend.display           = false;
    Chart.defaults.global.tooltips.enabled         = false;

    // Elements
    Chart.defaults.global.elements.arc.borderWidth = 0;
    Chart.defaults.global.elements.arc.borderColor = 'transparent';

    function initChart() {

        var $this = $(this);
        var type = $this.attr('data-type');
        var chartData = $this.attr('data-data');

        var data = [];
        var backgroundColors = [];
        var partData = [];

        $.each(chartData.split(';'), function() {
            partData = this.split(':');
            data.push(parseInt(partData[1], 10));
            backgroundColors.push( THEME_COLORS[(partData[0] || 'primary').toUpperCase() || 'PRIMARY'] );
        });

        new Chart($this, {
            type: type,
            data: {
                datasets: [{
                    data: data,
                    backgroundColor: backgroundColors
                }]
            }
        });
    }

    $('.chart').each(initChart);


    /* -------------------------------------------------------------------------------------------------------------- *
     * jQueryUI Slide range
     * -------------------------------------------------------------------------------------------------------------- */

    $('.slider-range').each(function() {

        var $this = $(this),
            $val = $($this.attr('data-range-value')),
            min = parseInt($this.attr('data-range-min'), 10),
            max = parseInt($this.attr('data-range-max'), 10);

        $this.slider({
            range: 'max',
            step: 1,
            min: min,
            max: max,
            values: [min],
            slide: function(event, ui) {
                $val.val(ui.values[0]);
            }
        });

        $val.val(min);

    });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Sidebar navigation
     * -------------------------------------------------------------------------------------------------------------- */

    if (isMobile) {
        $body.removeClass('sidebar-expanded');
    }

    $('.sidebar-nav-dropdown-toggle').on('click', function(e) {

        // Prevent events
        e.preventDefault();

        var $this = $(this);
        var $parent = $(this).parent(),
            $collapse = $parent.find('.collapse');

        if ($this.hasClass('sidebar-nav-dropdown-open')) {
            $this.removeClass('sidebar-nav-dropdown-open');
            $collapse.collapse('hide');
        } else {
            $this.addClass('sidebar-nav-dropdown-open');
            $collapse.collapse('show');
        }

    });

    $('.sidebar').find('a[href="' + document.location.pathname + '"]').addClass('active');


    /* -------------------------------------------------------------------------------------------------------------- *
     * Sidebar toggle
     * -------------------------------------------------------------------------------------------------------------- */

    $('.sidebar-toggle').on('click', function(e) {

        e.preventDefault();
        e.stopPropagation();

        var $this = $(this);

        if ($body.hasClass('sidebar-expanded')) {

            $this.removeClass('open');
            $body.removeClass('sidebar-expanded');

            $('.sidebar').find('.collapse').collapse('hide').parent().removeClass('sb-dropdown-open');

        } else {
            $this.addClass('open');
            $body.addClass('sidebar-expanded');
        }

    });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Sidebar search form
     * -------------------------------------------------------------------------------------------------------------- */

    var $sidebarSearchForm = $('.sidebar-search-form');

    $sidebarSearchForm.find('.form-control')
        .on('focus', function() {
            $sidebarSearchForm.addClass('focus');
        });

    // onBlur event imitation (if button events not handled, bubble!)
    $(document).mouseup(function (event) {
        if ($sidebarSearchForm.has(event.target).length === 0 &&
            $sidebarSearchForm.hasClass('focus')) {
            $sidebarSearchForm.removeClass('focus');
        }
    });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Widgets: general styles
     * -------------------------------------------------------------------------------------------------------------- */

    $(document).on('click', '[data-widget-toggle="layer"]', function(e) {

        // Prevent events
        e.preventDefault();

        // Widget control parent widget
        var $widget = $($(this).parents('.widget')),
        // Widget target layer
            $target = $($(this).data('widget-target'));

        // Required
        if ($widget.length === 0 || $target.length === 0) return;

        // Set new active layer
        $target.toggleClass('widget-layer-active');
    });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Demo content: jqvmap
     * -------------------------------------------------------------------------------------------------------------- */

    var $widgetSalesRegions = $('#widget-sales-regions');

    var vectorMapWorldRegionsList = [
        'AE', 'AF', 'AG', 'AL', 'AM', 'AO', 'AR', 'AT', 'AU', 'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BI', 'BJ',
        'BN', 'BO', 'BR', 'BS', 'BT', 'BW', 'BY', 'BZ', 'CA', 'CD', 'CF', 'CG', 'CH',  'I', 'CL', 'CM', 'CN', 'CO',
        'CR', 'CU', 'CV', 'CY', 'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO', 'DZ', 'EC', 'EE', 'EG', 'ER', 'ES', 'ET', 'FI',
        'FJ', 'FK', 'FR', 'GA', 'GB', 'GD', 'GE', 'GF', 'GH', 'GL', 'GM', 'GN', 'GQ', 'GR', 'GT', 'GW', 'GY', 'HN',
        'HR', 'HT', 'HU', 'ID', 'IE', 'IL', 'IN', 'IQ', 'IR', 'IS', 'IT', 'JM', 'JO', 'JP', 'KE', 'KG', 'KH', 'KM',
        'KN', 'KP', 'KR', 'KW', 'KZ',  'A', 'LB', 'LC', 'LK', 'LR', 'LS', 'LT', 'LV', 'LY', 'MA', 'MD', 'MG', 'MK',
        'ML', 'MM', 'MN', 'MR', 'MT', 'MU', 'MV', 'MW', 'MX', 'MY', 'MZ', 'NA', 'NC', 'NE', 'NG', 'NI', 'NL', 'NO',
        'NP', 'NZ', 'OM', 'PA', 'PE', 'PF', 'PG', 'PH', 'PK', 'PL', 'PT', 'PY', 'QA', 'RE', 'RO', 'RS', 'RU', 'RW',
        'SA', 'SB', 'SC', 'SD', 'SE', 'SI', 'SK', 'SL', 'SN', 'SO', 'SR', 'ST', 'SV', 'SY', 'SZ', 'TD', 'TG', 'TH',
        'TJ', 'TL', 'TM', 'TN', 'TR', 'TT', 'TW', 'TZ', 'UA', 'UG', 'US', 'UY', 'UZ', 'VE', 'VN', 'VU', 'YE', 'ZA',
        'ZM', 'ZW'
    ];

    var vectorMapWorldRegionsListMax = vectorMapWorldRegionsList.length - 1;
    var vectorMapRegionsColors = [];
    var tmpRegion;
    var tmpRegionValue;
    var tmpRegionColor;
    var tmpRegionColorOpacity;

    for (var i = 0, l = 50; i < l; i++) {

        tmpRegion = (vectorMapWorldRegionsList[getRandomNumber(0,  vectorMapWorldRegionsListMax)]).toLowerCase();
        tmpRegionValue = getRandomNumber(500, 1000);

        if      (tmpRegionValue >= 500 && tmpRegionValue <   600) tmpRegionColor = THEME_COLORS.PRIMARY;
        else if (tmpRegionValue >= 600 && tmpRegionValue <   700) tmpRegionColor = THEME_COLORS.DEFAULT;
        else if (tmpRegionValue >= 700 && tmpRegionValue <   800) tmpRegionColor = THEME_COLORS.SUCCESS;
        else if (tmpRegionValue >= 800 && tmpRegionValue <   900) tmpRegionColor = THEME_COLORS.WARNING;
        else if (tmpRegionValue >= 900 && tmpRegionValue <= 1000) tmpRegionColor = THEME_COLORS.DANGER;

        tmpRegionColorOpacity = Math.max(tmpRegionValue % 100 / 100, .6) * 100;
        vectorMapRegionsColors[tmpRegion] = hex2RGBA(tmpRegionColor, tmpRegionColorOpacity);
    }

    var $widgetSalesRegionsMap = $('#demo-jqvmap');

    if ($widgetSalesRegionsMap.length > 0) {
        $widgetSalesRegionsMap.vectorMap({

            map               : 'world_en',
            backgroundColor   : '#fff',
            borderColor       : '#fff',
            borderOpacity     : 0.25,
            borderWidth       : 1,
            color             : hex2RGBA(THEME_COLORS.DEFAULT, 100),
            hoverColor        : THEME_COLORS.PRIMARY,
            colors            : vectorMapRegionsColors,
            enableZoom        : true,
            hoverOpacity      : .8,
            normalizeFunction : 'linear',
            scaleColors       : ['#b6d6ff', '#005ace'],
            selectedColor     : THEME_COLORS.PRIMARY,
            selectedRegions   : null,
            showTooltip       : true,

            onRegionClick: function(element, code, region) {

                var $loader = $('<div>').addClass('loader');

                $widgetSalesRegions.find('.wg-left').append($loader);
                $loader.fadeIn();

                setTimeout(function() {

                    $widgetSalesRegions.find('.wg-region-name').html(region);

                    // Random data
                    var cntOrders    = getRandomNumber(100, 999),
                        cntSales     = getRandomNumber(100, 999),
                        cntCustomers = getRandomNumber(100, 999),
                        diffSummary  = getRandomNumber(  1, 100);

                    $widgetSalesRegions.find('.wg-orders-value').html(cntOrders);
                    $widgetSalesRegions.find('.wg-sales-value').html(cntSales);
                    $widgetSalesRegions.find('.wg-customers-value').html(cntCustomers);
                    $widgetSalesRegions.find('.wg-summary .wg-value').html(diffSummary);

                    $loader.fadeOut();

                    setTimeout(function() { $loader.remove(); }, 300);

                }, 500);
            }
        });
    }

    var $widgetSalesRegionsHeight = $widgetSalesRegions.css('height');

    function setWidgetSalesRegionsHeight() {

        if (typeof $widgetSalesRegionsHeight === 'undefined') return;

        if ($(window).width() < 992) {
            $widgetSalesRegions.css('height', '');
        } else {
            $widgetSalesRegions.css('height', $widgetSalesRegionsHeight);
        }
    }

    setWidgetSalesRegionsHeight();
    $(window).on('resize', setWidgetSalesRegionsHeight);


    /* -------------------------------------------------------------------------------------------------------------- *
     * Demo content: calendar
     * -------------------------------------------------------------------------------------------------------------- */

    $('.wg-calendar-wrapper').calendar({
        onRender: function(month, year) {
            $('#widget-calendar-month-year').html(month + ' ' + year);
        }
    });

    var $widgetCalendar = $('.widget-calendar');
    var currentDate = new Date();

    $widgetCalendar.find('.wg-today-number').html(currentDate.getDate());
    $widgetCalendar.find('.wg-today-week-day').html(DAYS_NAMES[currentDate.getDay()]);
    $widgetCalendar.find('.wg-today-month').html(MONTHS_NAMES[currentDate.getMonth()]);
    $widgetCalendar.find('.wg-today-year').html(currentDate.getFullYear());


    /* -------------------------------------------------------------------------------------------------------------- *
     * Dual Paneled Widgets
     * -------------------------------------------------------------------------------------------------------------- */

    $('.widget-dual-toggle').on('click', function(e) {

        e.preventDefault();

        var $panels = $(this).siblings('.widget-dual-panels');

        if ($panels.hasClass('widget-dual-right')) {
            $panels.removeClass('widget-dual-right')
        } else {
            $panels.addClass('widget-dual-right')
        }
    });


    /* -------------------------------------------------------------------------------------------------------------- *
     * Finish loading
     * -------------------------------------------------------------------------------------------------------------- */

    $(window).on('load', function() {

        $('body').addClass('loaded');

        setTimeout(function() {
            $('.preloader').fadeOut('slow');
        }, 300);

    });




    /* -------------------------------------------------------------------------------------------------------------- *
     *
     * CHARTS (DEMO PAGES)
     *
     * -------------------------------------------------------------------------------------------------------------- */

    var $widgetSiteVisitsChart = $('#widget-site-visits-chart');
    if ($widgetSiteVisitsChart.length > 0) {
        frappe.call("dashboard_z.www.dashboard.get_last_6_months").then( ({message}) => {
            const {headers, ins_amt, pri_amt, maximum} = message;
            new Chart($widgetSiteVisitsChart, {
                type: 'bar',
                data: {
                    labels: headers,
                    datasets: [{
                        label: ' Consultas Privadas',
                        data: pri_amt,
                        backgroundColor: hex2RGBA(THEME_COLORS.DEFAULT, 100)
                    }, {
                        label: ' Consultas Seguros',
                        data: ins_amt,
                        backgroundColor: hex2RGBA(THEME_COLORS.DANGER, 100)
                    }]
                },
                options: {
                    responsive: true,
                    legend: { display: true },
                    scales: {
                        xAxes: [{
                            gridLines: {
                                display: false,
                                zeroLineColor: 'transparent'
                            }
                        }],
                        yAxes: [{
                            ticks: {
                                min: 0,
                                max: maximum,
                                stepSize: maximum / 5.0,
                                beginAtZero: true
                            },
                            gridLines: {
                                zeroLineColor: 'transparent'
                            }
                        }]
                    }
                }
            });
        });
    }

    var $widgetTrafficSourcesChart = $('#widget-traffic-sources-chart');
    if ($widgetTrafficSourcesChart.length > 0) {

        new Chart($widgetTrafficSourcesChart, {
            type: 'doughnut',
            data: {
                labels: ['PC', 'Tablet', 'Mobile'],
                datasets: [{
                    label: ' CPU usage',
                    data: getRandomDataArray(700, 1000, 3),
                    backgroundColor: [
                        hex2RGBA(THEME_COLORS.INFO,    90),
                        hex2RGBA(THEME_COLORS.SUCCESS, 90),
                        hex2RGBA(THEME_COLORS.DANGER,  90)
                    ],
                    borderColor: '#fff',
                    hoverBorderColor: '#fff',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: {
                    display: false
                }
            }
        });
    }



    /* -------------------------------------------------------------------------------------------------------------- *
     *
     * CHARTS (DOCUMENTATION PAGE)
     *
     * -------------------------------------------------------------------------------------------------------------- */

    /*
     * Line Chart
     * ========== */

    var $demo_chart_line = $('#demo-chart-line');
    if ($demo_chart_line.length > 0) {
        new Chart($demo_chart_line, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: ' Current Week Visits',
                    data: [879, 980, 594, 398, 1345, 1101, 1469],
                    backgroundColor: hex2RGBA(THEME_COLORS.PRIMARY, 100),
                    borderColor: hex2RGBA(THEME_COLORS.PRIMARY, 100),
                    borderWidth: 3,
                    pointRadius: 3,
                    pointHitRadius: 5,
                    fill: false
                }, {
                    label: ' Last Week Visits',
                    data: [787, 591, 398, 402, 786, 978, 1150],
                    backgroundColor: hex2RGBA(THEME_COLORS.SECONDARY, 100),
                    borderColor: hex2RGBA(THEME_COLORS.SECONDARY, 100),
                    borderWidth: 3,
                    pointRadius: 3,
                    pointHitRadius: 5,
                    fill: false
                }]
            },
            options: {
                legend: { display: false },
                scales: {
                    xAxes: [{
                        gridLines: {
                            zeroLineColor: 'transparent'
                        }
                    }],
                    yAxes: [{
                        gridLines: {
                            drawTicks: false,
                            display: false
                        },
                        ticks: {
                            beginAtZero: true
                        }
                    }]
                }
            }
        });
    }

    /*
     * Bar Chart
     * ========= */

    var $demo_chart_bar = $('#demo-chart-bar');
    if ($demo_chart_bar.length > 0) {
        new Chart($demo_chart_bar, {
            type: 'bar',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: ' Current Week Visits',
                    data: [879, 980, 594, 398, 1345, 1101, 1469],
                    backgroundColor: [
                        hex2RGBA(THEME_COLORS.PRIMARY, 100),
                        hex2RGBA(THEME_COLORS.INFO, 100),
                        hex2RGBA(THEME_COLORS.SUCCESS, 100),
                        hex2RGBA(THEME_COLORS.WARNING, 100),
                        hex2RGBA(THEME_COLORS.DARK, 100),
                        hex2RGBA(THEME_COLORS.DANGER, 100),
                        hex2RGBA(THEME_COLORS.PRIMARY, 100)
                    ],
                    borderColor: [
                        hex2RGBA(THEME_COLORS.PRIMARY, 100),
                        hex2RGBA(THEME_COLORS.INFO, 100),
                        hex2RGBA(THEME_COLORS.SUCCESS, 100),
                        hex2RGBA(THEME_COLORS.WARNING, 100),
                        hex2RGBA(THEME_COLORS.DARK, 100),
                        hex2RGBA(THEME_COLORS.DANGER, 100),
                        hex2RGBA(THEME_COLORS.PRIMARY, 100)
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                legend: { display: false },
                scales: {
                    yAxes: [{ ticks: { beginAtZero:true } }]
                }
            }
        });
    }

    /*
     * Radar Chart
     * =========== */

    var $demo_chart_radar = $('#demo-chart-radar');
    if ($demo_chart_radar.length > 0) {
        new Chart($demo_chart_radar, {
            type: 'radar',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [
                    {

                        label: ' Current Week Visits',
                        backgroundColor: hex2RGBA(THEME_COLORS.SECONDARY, 50),

                        borderWidth: 1,
                        borderColor: hex2RGBA(THEME_COLORS.SECONDARY, 70),

                        pointBackgroundColor: hex2RGBA(THEME_COLORS.SECONDARY, 70),
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: hex2RGBA(THEME_COLORS.SECONDARY, 70),

                        data: [879, 891, 1054, 398, 1345, 1101, 1469]
                    },
                    {

                        label: ' Last Week Visits',
                        backgroundColor: hex2RGBA(THEME_COLORS.DARK, 50),

                        borderWidth: 1,
                        borderColor: hex2RGBA(THEME_COLORS.DARK, 70),

                        pointBackgroundColor: hex2RGBA(THEME_COLORS.DARK, 70),
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: hex2RGBA(THEME_COLORS.DARK, 70),

                        data: [1500, 891, 398, 1000, 786, 978, 1150]
                    }
                ]
            },
            options: {
                legend: { display: false },
                scales: {
                    yAxes: [{
                        display: false,
                        ticks: { beginAtZero: true }
                    }]
                }
            }
        });
    }

    /*
     * Polar Area Chart
     * ================ */

    var $demo_chart_polar_area_preview = $('#demo-chart-polar-area-preview');
    if ($demo_chart_polar_area_preview.length > 0) {
        new Chart($demo_chart_polar_area_preview, {
            type: 'polarArea',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                datasets: [{
                    label: ' Current Week Visits',
                    data: [879, 980, 594, 398, 1345, 1101],
                    backgroundColor: [
                        hex2RGBA(THEME_COLORS.PRIMARY, 100),
                        hex2RGBA(THEME_COLORS.INFO, 100),
                        hex2RGBA(THEME_COLORS.SUCCESS, 100),
                        hex2RGBA(THEME_COLORS.WARNING, 100),
                        hex2RGBA(THEME_COLORS.DANGER, 100),
                        hex2RGBA(THEME_COLORS.DARK, 100)
                    ],
                    borderColor: '#fff',
                    hoverBorderColor: '#fff',
                    borderWidth: 1,
                    highlight: "#A8B3C5"
                }]
            },
            options: {
                legend: { display: false },
                scales: {
                    yAxes: [{ ticks: { beginAtZero: true } }]
                }
            }
        });
    }

    var $demo_chart_polar_area = $('#demo-chart-polar-area');
    if ($demo_chart_polar_area.length > 0) {
        new Chart($demo_chart_polar_area, {
            type: 'polarArea',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
                datasets: [{
                    label: ' Current Week Visits',
                    data: [879, 980, 594, 398, 1345, 1101],
                    backgroundColor: [
                        hex2RGBA(THEME_COLORS.PRIMARY, 100),
                        hex2RGBA(THEME_COLORS.INFO, 100),
                        hex2RGBA(THEME_COLORS.SUCCESS, 100),
                        hex2RGBA(THEME_COLORS.WARNING, 100),
                        hex2RGBA(THEME_COLORS.DANGER, 100),
                        hex2RGBA(THEME_COLORS.DARK, 100)
                    ],
                    borderColor: '#fff',
                    hoverBorderColor: '#fff',
                    borderWidth: 1,
                    highlight: "#A8B3C5"
                }]
            },
            options: {
                legend: { display: false },
                scales: {
                    yAxes: [{ ticks: { beginAtZero: true } }]
                }
            }
        });
    }

    /*
     * Pie Chart
     * ========= */

    var $demo_chart_pie = $('#demo-chart-pie');
    if ($demo_chart_pie.length > 0) {
        new Chart($demo_chart_pie, {
            type: 'pie',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
                datasets: [{
                    label: ' Current Week Visits',
                    data: [879, 980, 594, 398, 1345],
                    backgroundColor: [
                        hex2RGBA(THEME_COLORS.PRIMARY, 100),
                        hex2RGBA(THEME_COLORS.INFO, 100),
                        hex2RGBA(THEME_COLORS.SUCCESS, 100),
                        hex2RGBA(THEME_COLORS.DANGER, 100),
                        hex2RGBA(THEME_COLORS.DARK,100)
                    ],
                    borderColor: '#fff',
                    hoverBorderColor: '#fff',
                    borderWidth: 1
                }]
            },
            options: {
                legend: {
                    display: false
                },
                title: {
                    display : true,
                    text    : 'Pie chart',
                    fontSize: 14,
                    color   : '#555'
                }
            }
        });
    }

    /*
     * Doughnut Chart
     * ============== */

    var $demo_chart_doughnut = $('#demo-chart-doughnut');
    if ($demo_chart_doughnut.length > 0) {
        new Chart($demo_chart_doughnut, {
            type: 'doughnut',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
                datasets: [{
                    label: ' Current Week Visits',
                    data: [879, 980, 594, 398, 1345],
                    backgroundColor: [
                        hex2RGBA(THEME_COLORS.PRIMARY, 100),
                        hex2RGBA(THEME_COLORS.INFO, 100),
                        hex2RGBA(THEME_COLORS.SUCCESS, 100),
                        hex2RGBA(THEME_COLORS.DANGER, 100),
                        hex2RGBA(THEME_COLORS.DARK, 100)
                    ],
                    borderColor: '#fff',
                    hoverBorderColor: '#fff',
                    borderWidth: 1
                }]
            },
            options: {
                legend: {
                    display: false
                },
                title: {
                    display : true,
                    text    : 'Doughnut chart',
                    fontSize: 14,
                    color   : '#555'
                }
            }
        });
    }

})(jQuery);
